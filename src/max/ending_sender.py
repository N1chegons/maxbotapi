import asyncio
from datetime import datetime

from src.logger_config import setup_logger
from src.max.manager_sending import send_notification_max
from src.max.models import MemoryMode, User
from src.max.repository import MaxService
from src.telegram.manager_sending import send_notification_telegram
from src.yandexai.config import THEMES_INDEXES
from src.yandexai.orchestrator import ask_ai_with_index

logger = setup_logger('max_bot', 'max', 'MAX_bot.log')

async def ending_session(user_id: int, user, platform: str):
    session_user = await MaxService.get_session(user_id)
    logger.info(f"Пользователь {user_id} заканчивает диалог")

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        if platform == "MAX":
            await send_notification_max(user_id, "Данные не найдены.\n\nИспользуйте команду /new")
        else:
            await send_notification_telegram(user_id, "Данные не найдены.\n\nИспользуйте команду /new")
    else:
        history = await MaxService.get_history(user_id)
        logger.info(f"Получена история сообщений для пользоватля {user_id}")

        selected_topic = "Консультации"
        index_id = THEMES_INDEXES.get(selected_topic)
        text = f"""
            ПРОМТ для команды /end
                Проанализируй сообщения пользователя и коротко перечисли темы, которые обсудили, плюс выводы, к которым пришли.

            Вот все сообщения пользоватля:
            {history}
            """

        answer = ask_ai_with_index(index_id, text, selected_topic, history)

        if user.memory_mode == MemoryMode.session:
            logger.info(f"Пользователь {user_id} заканчивает диалог с памятью {MemoryMode.session}")
            await MaxService.delete_messages(user.user_id)
            if platform == "MAX":
                await send_notification_max(user_id, answer)
            else:
                await send_notification_telegram(user_id, answer)

        elif user.memory_mode == MemoryMode.full:
            logger.info(f"Пользователь {user_id} заканчивает диалог с памятью {MemoryMode.full}")
            if platform == "MAX":
                await send_notification_max(user_id, answer)
            else:
                await send_notification_telegram(user_id, answer)

async def send_daily_checkin(user):
    message = "Привет👋 Что делал прошедшие сутки? Давай обсудим?"

    if user.platform == "MAX":
        await send_notification_max(user.user_id, message)
    else:
        await send_notification_telegram(user.user_id, message)

async def process_inactive_users():
    """Основная функция"""
    now = datetime.utcnow()

    end_users = await MaxService.get_users_silent_between(1, 5)
    for user in end_users:
        try:
            await ending_session(user.user_id, user, user.platform)
            logger.info(f"/end отправлен {user.user_id}")
        except Exception as e:
            logger.error(f"Ошибка /end для {user.user_id}: {e}")

    daily_users = await MaxService.get_users_silent_between(1440, 1460)
    for user in daily_users:
        try:
            await send_daily_checkin(user)
            logger.info(f"Daily отправлен {user.user_id}")
        except Exception as e:
            logger.error(f"Ошибка daily для {user.user_id}: {e}")

def run():
    asyncio.run(process_inactive_users())

if __name__ == "__main__":
    run()