import asyncio
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.logger_config import setup_logger
from src.max.models import MemoryMode
from src.max.repository import MaxService
from src.yandexai.config import THEMES_INDEXES
from src.yandexai.orchestrator import ask_ai_with_index

logger = setup_logger('sender_bot', 'sender', 'sender_work.log')


# ==========================================
# УНИВЕРСАЛЬНАЯ ОТПРАВКА СООБЩЕНИЙ
# ==========================================
async def send_notification_by_bot(user_id: int, text: str, bot_name: str, platform: str = "MAX"):
    """
    Отправляет сообщение от нужного бота.

    Платформы:
    - MAX: MAX_Empathetic, MAX_Dominant
    - TELEGRAM: TELEGRAM_Empathic (эмпатичный)
    """
    try:
        if platform == "TELEGRAM":
            # Telegram — только эмпатичный бот
            from src.telegram.bot import bot
            logger.debug(f"Отправка в Telegram от эмпатичного бота")
        else:
            # MAX — выбираем бота по имени
            if bot_name == "MAX_Dominant":
                from src.max.bot_dominant.bot import bot
                logger.debug(f"Отправка в MAX от доминантного бота")
            else:
                from src.max.bot import bot
                logger.debug(f"Отправка в MAX от эмпатичного бота")

        await bot.send_message(user_id=user_id, text=text)
        logger.info(f"✅ Уведомление отправлено {user_id} (платформа: {platform}, бот: {bot_name})")

    except ImportError as e:
        logger.error(f"❌ Ошибка импорта бота для {platform}/{bot_name}: {e}")

    except Exception as e:
        logger.error(f"❌ Ошибка отправки {user_id} (платформа: {platform}, бот: {bot_name}): {e}")

# ==========================================
# ОСНОВНАЯ ФУНКЦИЯ /end
# ==========================================
async def ending_session(user_id: int, user, platform: str, bot_name: str = None):
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
            await send_notification_by_bot(user_id, msg, "MAX_Empathetic", platform)
            return

    logger.info(f"Пользователь {user_id} заканчивает диалог в боте {bot_name} (платформа: {platform})")

    # ====== ПРОВЕРКА СЕССИИ ======
    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        msg = "Данные не найдены.\n\nИспользуйте команду /new"
        await send_notification_by_bot(user_id, msg, bot_name, platform)
        return

    # ====== ПОЛУЧАЕМ ИСТОРИЮ ======
    history = await MaxService.get_history(user_id, bot_name)

    if not history:
        logger.info(f"У пользователя {user_id} нет истории в боте {bot_name}")
        msg = "У вас нет сообщений в этом боте."
        await send_notification_by_bot(user_id, msg, bot_name, platform)
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
        await send_notification_by_bot(user_id, msg, bot_name, platform)
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
        await send_notification_by_bot(user_id, msg, bot_name, platform)
        return

    # ====== ОТПРАВКА ОТВЕТА ======
    if user.memory_mode == MemoryMode.session:
        logger.info(f"Пользователь {user_id} заканчивает диалог с памятью {MemoryMode.session}")
        await MaxService.delete_messages(user_id)
        await send_notification_by_bot(user_id, answer, bot_name, platform)

    elif user.memory_mode == MemoryMode.full:
        logger.info(f"Пользователь {user_id} заканчивает диалог с памятью {MemoryMode.full}")
        await send_notification_by_bot(user_id, answer, bot_name, platform)
    else:
        logger.info(f"Пользователь {user_id} не использует память, итоги не отправлены")


# ==========================================
# ЕЖЕДНЕВНАЯ ПРОВЕРКА (только для эмпатичного)
# ==========================================
async def send_daily_checkin(user):
    """Ежедневное приветствие (только для эмпатичного бота)"""
    # Проверяем историю в зависимости от платформы
    if user.platform == "TELEGRAM":
        history = await MaxService.get_history(user.user_id, "TELEGRAM_Empathic", limit=1)
        bot_name = "TELEGRAM_Empathic"
    else:
        history = await MaxService.get_history(user.user_id, "MAX_Empathetic", limit=1)
        bot_name = "MAX_Empathetic"

    if not history:
        logger.info(f"У {user.user_id} нет истории в эмпатичном боте — daily пропущен")
        return

    message = "Привет👋 Что делал прошедшие сутки? Давай обсудим?"
    await send_notification_by_bot(user.user_id, message, bot_name, user.platform)
    logger.info(f"✅ Daily отправлен {user.user_id} (платформа: {user.platform})")

# ==========================================
# ОСНОВНОЙ ЦИКЛ ДЛЯ CRON
# ==========================================
async def process_inactive_users():
    # ====== 1️⃣ /end ДЛЯ ЭМПАТИЧНОГО И TELEGRAM ======
    end_users = await MaxService.get_users_silent_between(30, 50)
    logger.info(f"🔍 Найдено {len(end_users)} пользователей для /end (эмпатичный/telegram)")

    for user in end_users:
        try:
            bot_name = await MaxService.get_last_bot_for_user(user.user_id)
            if bot_name and bot_name != "MAX_Dominant":
                await ending_session(user.user_id, user, user.platform, bot_name)
                logger.info(f"/end отправлен {user.user_id} (бот: {bot_name})")
        except Exception as e:
            logger.error(f"Ошибка /end для {user.user_id}: {e}")

    # ====== 2️⃣ /end ДЛЯ ДОМИНАНТНОГО БОТА ======
    end_users_dominant = await MaxService.get_users_silent_between(30, 50, "MAX_Dominant")
    logger.info(f"🔍 Найдено {len(end_users_dominant)} пользователей для /end (доминантный)")

    for user in end_users_dominant:
        try:
            await ending_session(user.user_id, user, user.platform, "MAX_Dominant")
            logger.info(f"/end отправлен {user.user_id} (доминантный)")
        except Exception as e:
            logger.error(f"Ошибка /end для {user.user_id}: {e}")

    # ====== 3️⃣ DAILY (только эмпатичный) ======
    daily_users = await MaxService.get_users_silent_between(1440, 1456)
    for user in daily_users:
        try:
            history = await MaxService.get_history(user.user_id, "MAX_Empathetic", limit=1)
            if history:
                await send_daily_checkin(user)
                logger.info(f"Daily отправлен {user.user_id}")
        except Exception as e:
            logger.error(f"Ошибка daily для {user.user_id}: {e}")
def run():
    asyncio.run(process_inactive_users())


if __name__ == "__main__":
    run()