import logging

async def send_notification_telegram(user_id: int, text: str):
    """Отправляет уведомление пользователю в MAX"""
    try:
        from src.telegram.bot import bot
        await bot.send_message(chat_id=user_id, text=text)
        logging.info(f"✅ Уведомление отправлено пользователю {user_id}")
    except Exception as e:
        logging.error(f"❌ Не удалось отправить уведомление {user_id}: {e}")