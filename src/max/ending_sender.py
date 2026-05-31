from src.logger_config import setup_logger
from src.max.manager_sending import send_notification_max
from src.max.models import MemoryMode
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