import asyncio
import sys

project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.max.repository import MaxService
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
            op_id = payment_data["payment_id"]
            logger.info(f"Платежный ID и ссылка получены: {payment_link} --- {op_id}")

            # Формируем сообщение
            text = "Бот на связи! Ребята, у самых первых пользователей заканчивается время теста. Мы благодарны за участие и предлагаем оплатить первый месяц за 111 рублей. Ещё раз спасибо! Мы продолжаем работу и надеемся на ваши подсказки через команду /bot"
            # Отправляем в зависимости от платформы
            if user.platform == "TELEGRAM":
                await send_payment_telegram(user.user_id, text, payment_link, op_id)
            elif user.platform == "MAX":
                await send_payment_max(user.user_id, text, payment_link, op_id)
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

async def send_payment_telegram(chat_id: int, text: str, payment_link: str, op_id):
    """Отправляет сообщение с кнопкой в Telegram"""
    from src.telegram.bot import bot
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, \
        KeyboardButton

    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton(text="💳 Оплатить 111 ₽", url=payment_link))
    await TochkaApiService.save_payment(
        user_id=chat_id,
        operation_id=op_id,
        amount=111
    )
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)

async def send_payment_max(user_id: int, text: str, payment_link: str, op_id):
    """Отправляет сообщение с кнопкой в MAX"""
    from src.max.bot import bot
    from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
    from maxapi.types import LinkButton

    builder = InlineKeyboardBuilder()
    builder.row(LinkButton(text="💳 Оплатить 111 ₽", url=payment_link))
    await TochkaApiService.save_payment(
        user_id=user_id,
        operation_id=op_id,
        amount=111
    )
    await bot.send_message(
        user_id=user_id,
        text=text,
        attachments=[builder.as_markup()]
    )

def run():
    asyncio.run(send_payment_broadcast())


if __name__ == "__main__":
    run()