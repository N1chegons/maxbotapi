import re
import asyncio
from vkbottle import API
from src.config import settings
from src.logger_config import setup_logger
from src.vk_bot.repository import VkFactRepository

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

        post_text = fact.title
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


async def main():
    await FactSenderService.send_fact()


if __name__ == '__main__':
    asyncio.run(main())