import asyncio
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.logger_config import setup_logger
from src.max.manager_sending import send_notification_max
from src.max.models import MemoryMode
from src.max.repository import MaxService
from src.telegram.manager_sending import send_notification_telegram
from src.yandexai.config import THEMES_INDEXES
from src.yandexai.orchestrator import ask_ai_with_index

logger = setup_logger('sender_bot', 'sender', 'sender_work.log')


# ==========================================
# ОСНОВНАЯ ФУНКЦИЯ /end
# ==========================================
async def ending_session(user_id: int, user, platform: str, bot_name: str):
    """
    Подводит итоги диалога для пользователя.
    Если bot_name не указан — определяется автоматически по последнему сообщению.
    """
    session_user = await MaxService.get_session(user_id)

    # ====== ОПРЕДЕЛЯЕМ БОТА ======
    if not bot_name:
        bot_name = await MaxService.get_last_bot_for_user(user_id)
        if not bot_name:
            logger.warning(f"Не удалось определить последнего бота для {user_id}")
            msg = "Не удалось определить бота для подведения итогов."
            if platform == "MAX":
                await send_notification_max(user_id, msg)
            else:
                await send_notification_telegram(user_id, msg)
            return

    logger.info(f"Пользователь {user_id} заканчивает диалог в боте {bot_name}")

    # ====== ПРОВЕРКА СЕССИИ ======
    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        msg = "Данные не найдены.\n\nИспользуйте команду /new"
        if platform == "MAX":
            await send_notification_max(user_id, msg)
        else:
            await send_notification_telegram(user_id, msg)
        return

    # ====== ПОЛУЧАЕМ ИСТОРИЮ ======
    history = await MaxService.get_history(user_id, bot_name)

    if not history:
        logger.info(f"У пользователя {user_id} нет истории в боте {bot_name}")
        msg = f"У вас нет сообщений в этом боте."
        if platform == "MAX":
            await send_notification_max(user_id, msg)
        else:
            await send_notification_telegram(user_id, msg)
        return

    logger.info(f"Получена история сообщений для пользователя {user_id} (бот: {bot_name})")

    # ====== ВЫБОР ТЕМЫ ======
    if bot_name == "MAX_Dominant":
        selected_topic = "Мировоззрение"
    else:
        selected_topic = "Консультации"

    index_id = THEMES_INDEXES.get(selected_topic)
    if not index_id:
        logger.error(f"Не найден индекс для темы {selected_topic}")
        msg = "Ошибка: не удалось найти индекс для подведения итогов."
        if platform == "MAX":
            await send_notification_max(user_id, msg)
        else:
            await send_notification_telegram(user_id, msg)
        return

    # ====== ФОРМИРУЕМ ПРОМТ ======
    text = f"""
        ПРОМТ для команды /end
        Проанализируй сообщения пользователя и коротко перечисли темы, которые обсудили, плюс выводы, к которым пришли.

        Вот все сообщения пользователя:
        {history}
    """

    answer = ask_ai_with_index(index_id, text, selected_topic, history)

    if not answer:
        logger.error(f"Не удалось получить ответ от AI для {user_id}")
        msg = "⚠️ Не удалось подвести итоги. Попробуйте позже."
        if platform == "MAX":
            await send_notification_max(user_id, msg)
        else:
            await send_notification_telegram(user_id, msg)
        return

    # ====== ОТПРАВКА ОТВЕТА ======
    if user.memory_mode == MemoryMode.session:
        logger.info(f"Пользователь {user_id} заканчивает диалог с памятью {MemoryMode.session}")
        await MaxService.delete_messages(user_id)
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
    else:
        logger.info(f"Пользователь {user_id} не использует память, итоги не отправлены")


# ==========================================
# ЕЖЕДНЕВНАЯ ПРОВЕРКА
# ==========================================
async def send_daily_checkin(user):
    """Ежедневное приветствие (только для эмпатичного бота)"""
    message = "Привет👋 Что делал прошедшие сутки? Давай обсудим?"

    if user.platform == "MAX":
        await send_notification_max(user.user_id, message)
    else:
        await send_notification_telegram(user.user_id, message)


# ==========================================
# ОСНОВНОЙ ЦИКЛ
# ==========================================
async def process_inactive_users():
    # ====== 1️⃣ /end ЧЕРЕЗ 30-50 МИНУТ ======
    end_users = await MaxService.get_users_silent_between(30, 50)

    for user in end_users:
        try:
            bot_name = await MaxService.get_last_bot_for_user(user.user_id)
            if bot_name:
                await ending_session(user.user_id, user, user.platform, bot_name)
                logger.info(f"/end отправлен {user.user_id} (бот: {bot_name})")
            else:
                logger.info(f"У {user.user_id} нет сообщений ни в одном боте — пропускаем")
        except Exception as e:
            logger.error(f"Ошибка /end для {user.user_id}: {e}")

    # ====== 2️⃣ DAILY ЧЕРЕЗ 24 ЧАСА (ТОЛЬКО ДЛЯ ЭМПАТИЧНОГО) ======
    daily_users = await MaxService.get_users_silent_between(1440, 1456)

    for user in daily_users:
        try:
            # Проверяем, есть ли история в эмпатичном боте
            history = await MaxService.get_history(user.user_id, "MAX_Empathetic", limit=1)
            if history:
                await send_daily_checkin(user)
                logger.info(f"Daily отправлен {user.user_id} (эмпатичный)")
            else:
                logger.info(f"У {user.user_id} нет истории в эмпатичном боте — daily пропущен")
        except Exception as e:
            logger.error(f"Ошибка daily для {user.user_id}: {e}")


def run():
    asyncio.run(process_inactive_users())


if __name__ == "__main__":
    run()