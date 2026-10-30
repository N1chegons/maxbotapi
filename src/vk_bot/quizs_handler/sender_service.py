import re
import asyncio
from vkbottle import API
from src.config import settings
from src.logger_config import setup_logger
from src.vk_bot.repository import VkFactRepository, VkOpinionRepository

logger = setup_logger('sender_service_vk', 'vk', 'sender_service_vk.log')

class FactSenderService:
    VK_TOKEN = settings.VK_TOKEN_COMMUNITY
    GROUP_ID = -216257056
    api = API(VK_TOKEN)

    @classmethod
    async def send_fact(cls):
        fact = await VkFactRepository.get_random_fact()

        if not fact:
            logger.warning("Фактов не найдено. База пуста")
            return

        post_text = f"Фак дня💡\n{fact.title}"
        full_url = fact.video_url if hasattr(fact, 'video_url') else fact.url

        attachment = None
        if full_url:
            match = re.search(r'(video-?\d+_\d+)', full_url)
            if match:
                attachment = match.group(1)
            else:
                attachment = full_url

        try:
            logger.info(f"Попытка отправки поста из БД. Название факта - {post_text}\nСсылка на факт - {full_url}")
            response = await cls.api.wall.post(
                owner_id=cls.GROUP_ID,
                from_group=1,
                message=post_text,
                attachments=attachment
            )

            post_id = response.post_id

            logger.info(f"✅ Пост опубликован. ID:{post_id}.\nСсылка на пост: https://vk.com/wall{cls.GROUP_ID}_{post_id}")


        except Exception as e:
            logger.error(f"❌ Ошибка публикации: {e}")

    @classmethod
    async def send_opinion(cls):
        mailing = await VkOpinionRepository.get_random_opinion()

        if not mailing:
            logger.warning("Сборов не найдено. База пуста")
            return

        post_text = mailing.title
        full_url = mailing.video_url if hasattr(mailing, 'video_url') else mailing.url
        chat_link = "https://vk.me/club216257056?ref=opinion"
        post_text = f"{mailing.text_message}\n\n👉 [Высказать мнение]({chat_link})"

        attachment = None
        if full_url:
            match = re.search(r'(video-?\d+_\d+)', full_url)
            if match:
                attachment = match.group(1)
            else:
                attachment = full_url

        try:
            logger.info(f"Попытка отправки поста из БД. Название сбора мнений - {post_text}\nСсылка на факт - {full_url}")
            response = await cls.api.wall.post(
                owner_id=cls.GROUP_ID,
                from_group=1,
                message=post_text,
                attachments=attachment
            )

            post_id = response.post_id

            logger.info(
                f"✅ Пост опубликован. ID:{post_id}.\nСсылка на пост: https://vk.com/wall{cls.GROUP_ID}_{post_id}")


        except Exception as e:
            logger.error(f"❌ Ошибка публикации: {e}")