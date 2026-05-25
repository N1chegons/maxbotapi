import logging

async def send_notification_max(user_id: int, text: str):
    try:
        from src.max.bot import bot
        await bot.send_message(user_id=user_id, text=text)
        logging.info(f"✅ Уведомление отправлено пользователю {user_id}")
    except Exception as e:
        logging.error(f"❌ Не удалось отправить уведомление {user_id}: {e}")