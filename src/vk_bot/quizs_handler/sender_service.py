import re
import json
import asyncio
from vkbottle import API
from src.config import settings
from src.logger_config import setup_logger
from src.vk_bot.repository import VkFactRepository, VkOpinionRepository, VkTestRepository

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
        post_text = f"{mailing.title}\n\n👉 Высказать мнение: {chat_link}"

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

    @classmethod
    async def send_tests(cls):
        test = await VkTestRepository.get_random_test()

        if not test:
            logger.warning("Тестов не найдено. База пуста")
            return

        try:

            answers_json = json.dumps(test.options)

            poll_response = await cls.api.polls.create(
                owner_id=cls.GROUP_ID,
                question=test.title,
                add_answers=answers_json,
                is_anonymous=1
            )
            poll_id = poll_response.id

            video_link = test.video_url
            post_text = f"👉 Посмотри видео, чтобы правильно ответить: {video_link}\n\n{test.title}"

            response = await cls.api.wall.post(
                owner_id=cls.GROUP_ID,
                from_group=1,
                message=post_text,
                attachments=f"poll{cls.GROUP_ID}_{poll_id}"
            )
            logger.info(f"✅ Тест-опрос опубликован. Ссылка: https://vk.com/wall{cls.GROUP_ID}_{response.post_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка публикации: {e}")

    VK_USER_TOKEN = "vk1.a.I_7btNu4bBfFZGNiWkJ9ldJlpHf2gpdgbOMnKiu7ncHdiboaXppylO6rxy867xhNYPcbBRhNUHp3cL3TMn5TmwhpuxT9Sh1oSSqOZ83OsfPvsfjyvyQENfzTQun7jzBybq1GNZvRgJbeKxGKB2YDHPsmfmMFkDJ6bwiORdJocFG9Iq-JZQt6ttHYnFD3WotlzE0cvS0OraEXCWgntRP83Q"
    USER_ID = 552367635

    @classmethod
    async def send_test(cls):
        test = await VkTestRepository.get_random_test()
        if not test:
            logger.warning("Тестов не найдено.")
            return

        # Создаем отдельный API с пользовательским токеном
        user_api = API(cls.VK_USER_TOKEN)

        try:
            # 1. Создаем опрос (передаем owner_id БЕЗ минуса - это твой профиль)
            answers_json = json.dumps(test.options)
            poll_response = await user_api.polls.create(
                owner_id=cls.USER_ID,
                question=test.title,
                add_answers=answers_json,
                is_anonymous=1
            )
            poll_id = poll_response.id
            logger.info(f"Опрос создан. ID: {poll_id}")

            # 2. Парсим ID видео (если оно есть)
            attachment = None
            if test.video_url:
                match = re.search(r'(video-?\d+_\d+)', test.video_url)
                if match:
                    attachment = match.group(1)
                else:
                    attachment = test.video_url

            # 3. Публикуем на стену
            # ВАЖНО: Постим от имени группы, используя токен СООБЩЕСТВА
            # А опрос прикрепляем в формате poll{USER_ID}_{POLL_ID}
            post_text = f"🤔 {test.title}\n\nПосмотри видео, чтобы правильно ответить!"

            attachments_list = [f"poll{cls.USER_ID}_{poll_id}"]
            if attachment:
                # Если есть видео, добавляем его вторым вложением (ВК позволяет опрос + медиа)
                attachments_list.append(attachment)

            response = await cls.api.wall.post(
                owner_id=cls.GROUP_ID,
                from_group=1,
                message=post_text,
                attachments=",".join(attachments_list)
            )

            logger.info(f"✅ Тест с опросом опубликован: https://vk.com/wall{cls.GROUP_ID}_{response.post_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка публикации теста: {e}")