import asyncio
from src.max.repository import MaxService
from src.max.models import User
from src.telegram.manager_sending import send_notification_telegram
from src.max.manager_sending import send_notification_max
from src.tochka_api.service import TochkaApiService
from src.logger_config import setup_logger

logger = setup_logger('broadcast', 'broadcast', 'broadcast.log')


async def send_payment_broadcast(amount: float = 111):
    """
    Отправляет всем пользователям сообщение с кнопкой оплаты.
    Для Telegram — InlineKeyboard со ссылкой.
    Для MAX — кнопка-ссылка.
    """
    # Получаем всех пользователей
    users = await MaxService.get_all_users()
    logger.info(f"Начинаем рассылку для {len(users)} пользователей")

    success = 0
    fail = 0

    for user in users:
        try:
            # Создаём платёжную ссылку
            payment_data = TochkaApiService().create_payment_link(
                amount=amount
            )

            if not payment_data or not payment_data.get("payment_link"):
                logger.error(f"Не удалось создать ссылку для {user.user_id}")
                fail += 1
                continue

            payment_link = payment_data["payment_link"]

            # Формируем сообщение
            text = "Бот на связи! Ребята, у самых первых пользователей заканчивается время теста. Мы благодарны за участие и предлагаем оплатить первый месяц за 111 рублей. Ещё раз спасибо! Мы продолжаем работу и надеемся на ваши подсказки через команду /bot"
            # Отправляем в зависимости от платформы
            if user.platform == "TELEGRAM":
                await send_payment_telegram(user.user_id, text, payment_link)
            elif user.platform == "MAX":
                await send_payment_max(user.user_id, text, payment_link)
            else:
                logger.warning(f"Неизвестная платформа: {user.platform}")
                continue

            success += 1
            logger.info(f"✅ Отправлено {user.user_id} ({user.platform})")

            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"❌ Ошибка для {user.user_id}: {e}")
            fail += 1

    logger.info(f"Рассылка завершена. Успешно: {success}, Ошибок: {fail}")


async def send_payment_telegram(chat_id: int, text: str, payment_link: str):
    """Отправляет сообщение с кнопкой в Telegram"""
    from src.telegram import bot
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, \
        KeyboardButton

    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton(text="💳 Оплатить 111 ₽", url=payment_link))
    await TochkaApiService.save_payment(
        user_id=chat_id,
        operation_id=payment_link,
        amount=111
    )
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)


async def send_payment_max(user_id: int, text: str, payment_link: str):
    """Отправляет сообщение с кнопкой в MAX"""
    from src.max import bot
    from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
    from maxapi.types import LinkButton

    builder = InlineKeyboardBuilder()
    builder.row(LinkButton(text="💳 Оплатить 111 ₽", url=payment_link))
    await TochkaApiService.save_payment(
        user_id=user_id,
        operation_id=payment_link,
        amount=111
    )
    await bot.send_message(
        user_id=user_id,
        text=text,
        attachments=[builder.as_markup()]
    )


async def send_test_payment(amount: float = 111):
    """Отправляет платёжное сообщение только тебе (для теста)"""
    from src.config import settings

    test_user_id = 8177043133  # твой Telegram ID (или MAX ID)

    # Платформа: попробуй Telegram
    platform = "TELEGRAM"

    payment_data = TochkaApiService().create_payment_link(
        amount=amount
    )

    if not payment_data or not payment_data.get("payment_link"):
        logger.error("Не удалось создать ссылку")
        return

    payment_link = payment_data["payment_link"]
    text = f"🧪 ТЕСТОВАЯ РАССЫЛКА\n\n💰 Сумма: {amount} руб.\n🔗 Ссылка: {payment_link}"

    await TochkaApiService.save_payment(
        user_id=test_user_id,
        operation_id=payment_link,
        amount=111
    )

    # Отправляем в Telegram
    from src.telegram import bot
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="💳 Оплатить тест", url=payment_link))

    await bot.send_message(chat_id=test_user_id, text=text, reply_markup=keyboard)
    logger.info(f"✅ Тестовая ссылка отправлена {test_user_id}")

def run():
    asyncio.run(send_payment_broadcast())


if __name__ == "__main__":
    run()