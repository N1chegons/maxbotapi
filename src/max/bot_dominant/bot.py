import asyncio
import subprocess
from datetime import datetime

import aiohttp
import magic
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import Command
from maxapi.types import MessageCreated, BotStarted, CallbackButton, LinkButton, MessageCallback
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.admin.repository import AdminService
from src.config import settings
from src.logger_config import setup_logger
from src.max.models import UserState, SubsStatus
from src.max.repository import MaxService, AudioService
from src.max.utils import upload_to_s3
from src.tochka_api.service import TochkaApiService
from src.yandexai.config import THEMES_INDEXES
from src.yandexai.orchestrator import ask_ai_with_index

logger = setup_logger('max_bot', 'max-2', 'MAX2_bot.log')

TOKEN = settings.MAX_BOT_TOKEN_2

bot = Bot(TOKEN)
dp = Dispatcher()

# logic
@dp.bot_started()
async def bot_started(event: BotStarted):
    user_id = event.user.user_id
    user = await MaxService.get_user(user_id)
    logger.info(f"Пользователь {user_id} запустил бота-2")

    if not user:
        await MaxService.create_user(user_id, "MAX")
        await MaxService.create_session(user_id)
        logger.info(f"Пользователь {user_id} успешно зарегестрировался")

    reply_kb = InlineKeyboardBuilder()
    reply_kb = InlineKeyboardBuilder()
    reply_kb.row(
        CallbackButton(
            text="Поехали >",
            payload="continue"
        ),
        LinkButton(
            text="про Бота >",
            url="https://disk.yandex.ru/i/Y1qvubfy9EwyOQ"
        ),
        LinkButton(
            text="про Эксперта >",
            url="https://disk.yandex.ru/i/RoQ3RiuyUyRYDA"
        ),
    )

    await bot.send_message(
        user_id=user_id,
        text=(
            "Привет 👋 "
            "Ты попал к доминантному боту, который тренируется говорить на острые темы 🤬 "
            "и тренирует тебя мыслить конструктивно 😉  Времена нынче опасные, на мозг давят капитально. Важно сохранять спокойствие при понимании, что происходит 🫡 \n\n"
            "Каждый разговор с ботом как урок истории: ты открываешь тему, он продавливает вывод 🤯 "
            "Победить бота не получится: он заставит тебя мыслить верно. Пробуй, разрушай сомнения."
        ),
        attachments=[reply_kb.as_markup()]
    )

@dp.message_created(Command('new'))
async def new_session(event: MessageCreated):
    user_id = event.message.sender.user_id
    user = await MaxService.get_user(user_id)
    logger.info(f"Пользователь {user_id} запустил бота-2 с помощью /new")

    if not user:
        await MaxService.create_user(user_id, "MAX")
        await MaxService.create_session(user_id)
        logger.info(f"Пользователь {user_id} успешно зарегестрировался")

    reply_kb = InlineKeyboardBuilder()
    reply_kb = InlineKeyboardBuilder()
    reply_kb.row(
        CallbackButton(
            text="Поехали >",
            payload="continue"
        ),
        LinkButton(
            text="про Бота >",
            url="https://disk.yandex.ru/i/Y1qvubfy9EwyOQ"
        ),
        LinkButton(
            text="про Эксперта >",
            url="https://disk.yandex.ru/i/RoQ3RiuyUyRYDA"
        ),
    )

    await bot.send_message(
        user_id=user_id,
        text=(
            "Привет 👋 "
            "Ты попал к доминантному боту, который тренируется говорить на острые темы 🤬 "
            "и тренирует тебя мыслить конструктивно 😉  Времена нынче опасные, на мозг давят капитально. Важно сохранять спокойствие при понимании, что происходит 🫡 \n\n"
            "Каждый разговор с ботом как урок истории: ты открываешь тему, он продавливает вывод 🤯 "
            "Победить бота не получится: он заставит тебя мыслить верно. Пробуй, разрушай сомнения."
        ),
        attachments=[reply_kb.as_markup()]
    )

@dp.message_created(Command('help'))
async def instruction(event: MessageCreated):
    user_id = event.message.sender.user_id

    reply_kb = InlineKeyboardBuilder()
    reply_kb.row(
        LinkButton(
            text="про Бота >",
            url="https://disk.yandex.ru/i/Y1qvubfy9EwyOQ"
        )
    )

    await bot.send_message(
        user_id=user_id,
        text=(
            "📋 **Что я умею:**\n\n"
            "🔁 /new — начать всё заново\n"
            "❓ /help — частые вопросы и видео про меня\n"
            "💳 /sub — проверить подписку, продлить или оплатить\n"
            "📅 /igor — записаться на живую консультацию с Игорем + видео\n"
            "🤖 /bot — отправить обращение в поддержку\n"
        ),
        attachments=[reply_kb.as_markup()]

    )

@dp.message_created(Command('bot'))
async def help_bot_command(event: MessageCreated):
    user_id = event.message.sender.user_id
    session_user = await MaxService.get_session(user_id)
    logger.info(f"Пользователь {user_id} отправил обращение")

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        await bot.send_message(
            user_id=user_id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    else:
        reply_kb = InlineKeyboardBuilder()
        reply_kb.row(
            CallbackButton(text="✅ ОТПРАВИТЬ", payload="bot_send_problem"),
            CallbackButton(text="❌ ОТМЕНА", payload="bot_dsend"),
        )

        await bot.send_message(
            user_id=user_id,
            text=(
                "Если бот где-то затупил, то жми на кнопку отправить. Богдан разберётся 😉"
            ),
            attachments=[reply_kb.as_markup()]
        )

async def create_payment_link_dominator(amount: float, user_id: int) :
    await asyncio.sleep(1)
    payment_data = TochkaApiService().create_payment_link(amount)
    logger.info(f"Создание ссылки на оплату (доминант) для пользователя {user_id}")
    if payment_data and payment_data.get("payment_link"):
        logger.info(f"Платежная ссылка (доминант) для пользователя {user_id} создана: {payment_data.get('payment_link')}")
        await TochkaApiService.save_payment(
            user_id=user_id,
            operation_id=payment_data["payment_id"],
            amount=amount,
            bot_name="MAX_Dominant"
        )
        return payment_data["payment_link"]

    logger.warning(f"Не удалось создать платежную ссылку (доминант) для пользователя {user_id}")
    return None
async def send_sub_buttons_dominator(user_id: int, user):
    kb = InlineKeyboardBuilder()

    if user.subscription_status_dominator in (SubsStatus.active, SubsStatus.grace_period):
        if user.subscription_ends_at_dominator and user.subscription_ends_at_dominator > datetime.utcnow():
            kb.row(CallbackButton(text="❌ Отменить подписку", payload="cancel_subscription_dominator"))
            await bot.send_message(user_id=user_id, text="🔧 Управление подпиской:", attachments=[kb.as_markup()])
            return

    if user.message_count_dominator < user.free_messages_limit_for_dominant:
        remaining = user.free_messages_limit_for_dominant - user.message_count_dominator
        info_text = f"📊 У вас осталось {remaining} бесплатных сообщений из {user.free_messages_limit_for_dominant}"
    else:
        info_text = "🔒 Бесплатные сообщения закончились"

    payment_link = await create_payment_link_dominator(1.00, user_id)
    kb.row(LinkButton(text="💳 Оплатить 333 ₽", url=payment_link))

    await bot.send_message(
        user_id=user_id,
        text=f"{info_text}\n\n💳 Оплатите подписку для продолжения:",
        attachments=[kb.as_markup()]
    )
async def get_subscription_status_dominator(user):
    now = datetime.utcnow()
    next_date = None

    if user.subscription_status_dominator in (SubsStatus.active, SubsStatus.grace_period):
        if user.subscription_ends_at_dominator and user.subscription_ends_at_dominator > now:
            next_date = user.subscription_ends_at_dominator
            status_text = "✅ Активна"
        else:
            status_text = "❌ Истекла"

    elif user.subscription_status_dominator == SubsStatus.cancelled:
        if user.subscription_ends_at_dominator and user.subscription_ends_at_dominator > now:
            next_date = user.subscription_ends_at_dominator
            status_text = "⏸ Отменена (доступ до даты)"
        else:
            status_text = "❌ Истекла "

    else:
        status_text = "❌ Нет активной подписки"

    return status_text, next_date

@dp.message_created(Command('sub'))
async def cmd_sub_dominator(event: MessageCreated):
    user_id = event.from_user.user_id
    user = await MaxService.get_user(user_id)
    logger.info(f"Проверка подписки (доминант) для пользователя {user_id}")

    if not user:
        logger.warning(f"Пользователь {user_id} не найден")
        await bot.send_message(user_id=user_id, text="❌ Пользователь не найден. Напишите /new")
        return

    status_text, next_date = await get_subscription_status_dominator(user)

    text = f"💳  Подписка\n"
    text += f"📌 Статус: {status_text}\n"
    text += f"💰 Тариф: Базовый (333 ₽/мес)\n"
    if next_date:
        days_left = (next_date - datetime.utcnow()).days
        text += f"📅 Следующее списание: {next_date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Осталось дней: {days_left}\n"

    await bot.send_message(user_id=user_id, text=text)
    await send_sub_buttons_dominator(user_id, user)

@dp.message_callback(F.callback.payload == "cancel_subscription_dominator")
async def cancel_subscription_callback(callback: MessageCallback):
    user_id = callback.callback.user.user_id

    user = await MaxService.get_user(user_id)

    if user.subscription_status_dominator not in (SubsStatus.active, SubsStatus.grace_period):
        logger.warning(f"Пользователь {user_id} не имеет активной подписки")
        await callback.message.edit(text="❌ У вас нет активной подписки для отмены.")
        return

    await MaxService.change_subscription_status_dominator(user_id, SubsStatus.cancelled)
    logger.info(f"Пользователь {user_id} успешно отменил подписку, статус подписки: {SubsStatus.cancelled}")

    await callback.message.edit(
        text=f"✅ Подписка отменена.\n"
             f"Доступ сохранится до {user.subscription_ends_at.strftime('%d.%m.%Y')}.\n"
             f"Чтобы возобновить, оплатите через /sub",
        attachments=[]
    )

@dp.message_callback(F.callback.payload == "bot_send_problem")
async def bot_report(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    history = await MaxService.get_last_messages_for_dominant(user_id, limit=20)

    history_text = "\n".join([
        f"{'🧑 Клиент' if msg.role == 'user' else '🤖 Бот'}: {msg.content}"
        for msg in history
    ])

    await AdminService.add_problem_request(
        client_id=user_id,
        messages=history_text
    )

    logger.info(f"Пользователь {user_id} отправил обращение")
    await callback.message.edit(
        text="✅ Обращение отправлено! Богдан разберётся в ближайшее время 😉",
        attachments=[]
    )

# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "bot_dsend")
async def bot_cancel(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    logger.info(f"Пользователь {user_id} остановил отправку обращения")

    await callback.message.edit(
        text="❌ Обращение отменено. Если передумаешь — напиши /bot",
        attachments=[]
    )


# text logic
@dp.message_created(F.message.body.text)
async def handle_message(event: MessageCreated):
    text = event.message.body.text
    if text.startswith('/'):
        return

    user_id = event.message.sender.user_id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    logger.info(f"Пользователь {user_id} отправил сообщение: {text[:10]}")

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    # if not session_user:
    #     logger.warning(f"У пользователя {user_id} не найдена сессия")
    #     await bot.send_message(
    #         user_id=user_id,
    #         text="Данные не найдены.\n\nИспользуйте команду /new"
    #     )

    if not await MaxService.can_send_message(user_id, "MAX_Dominant"):
        logger.warning(f"У пользователя {user_id} не активирована подписка - нет возможности писать")
        await bot.send_message(
            user_id=user_id,
            text="🔒 Ваша подписка не активна.\nПожалуйста, оплатите доступ в /sub"
        )

    else:
        selected_topic = "Мировоззрение"
        index_id = THEMES_INDEXES.get(selected_topic)
        history = await MaxService.get_history(user_id, "MAX_Dominant",  limit=200)
        answer = ask_ai_with_index(index_id, text, selected_topic, history)

        if answer:
            await MaxService.add_message(user_id, session_user.id, "user", text, "MAX_Dominant")
            await MaxService.add_message(user_id, session_user.id, "assistant", answer, "MAX_Dominant")
            await bot.send_message(user_id=user_id, text=answer)
            logger.info(f"Пользователь успешно получил ответ от ассистента")
        else:
            logger.error(f"Пользователь {user_id} не получил ответ")
            await bot.send_message(
                user_id=user_id,
                text="⚠️ Не удалось получить ответ. Попробуйте позже."
            )

@dp.message_created(F.message.body.attachments)
async def handle_voice_message(event: MessageCreated):
    user_id = event.message.sender.user_id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    logger.info(f"Пользователь {user_id} отправил голосовое сообщение")

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    if not await MaxService.can_send_message(user_id, "MAX_Dominant"):
        logger.warning(f"У пользователя {user_id} не активирована подписка - нет возможности писать")
        await bot.send_message(
            user_id=user_id,
            text="🔒 Ваша подписка не активна.\nПожалуйста, оплатите доступ в /sub"
        )

    else:
        selected_topic = "Мировоззрение"
        index_id = THEMES_INDEXES.get(selected_topic)
        history = await MaxService.get_history(user_id, "MAX_Dominant", limit=200)


        audio_attachment = None
        # noinspection PyTypeChecker
        for att in event.message.body.attachments:
            if att.type == "audio":
                audio_attachment = att
                break
        if not audio_attachment:
            return
        audio_url = audio_attachment.payload.url
        print(audio_url)

        try:
            headers = {"User-Agent": "MAX/1.0", "Referer": "https://max.ru/"}

            async with aiohttp.ClientSession() as session_audio:
                async with session_audio.get(audio_url, headers=headers) as resp:
                    audio_data = await resp.read()

            mime = magic.from_buffer(audio_data, mime=True)
            if mime != 'audio/ogg':
                process = subprocess.run(
                    ['ffmpeg', '-i', 'pipe:0', '-c:a', 'libopus', '-ar', '48000', '-b:a', '64k', '-f', 'ogg', 'pipe:1'],
                    input=audio_data,
                    capture_output=True
                )
                if process.returncode != 0:
                    raise Exception(process.stderr.decode())
                audio_data = process.stdout

            s3_url = await upload_to_s3(audio_data)

            recognized_text = AudioService.recognize_from_s3(s3_url, settings.YC_API_KEY)

            answer = ask_ai_with_index(index_id, recognized_text, selected_topic, history)

            if answer:
                # if user.memory_mode != MemoryMode.none:
                await MaxService.add_message(user_id, session_user.id, "user", recognized_text, "MAX_Dominant")
                await MaxService.add_message(user_id, session_user.id, "assistant", answer, "MAX_Dominant")
                await bot.send_message(user_id=user_id, text=answer)
                logger.info(f"Пользователь {user_id} успешно получил ответ от ассистента")
            else:
                logger.error(f"Пользователь {user_id} не получил ответ")
                await bot.send_message(
                    user_id=user_id,
                    text="⚠️ Не удалось получить ответ. Попробуйте позже."
                )

        except Exception as e:
            logger.exception(f"Ошибка обработки голосового сообщения от пользователя {user_id}, ошибка: {e}")
            await bot.send_message(user_id=user_id, text="⚠️ Ошибка обработки голосового. Попробуйте текстом.")

async def main():
    webhook_url = "https://bot.nepovinnyh.ru/webhook2"
    webhook_secret = settings.SECRET_WEBHOOK_KEY

    # Регистрируем новую на поддомен
    await bot.subscribe_webhook(url=webhook_url, secret=webhook_secret)

    await dp.handle_webhook(
        bot=bot,
        host='0.0.0.0',
        port=8082,
        secret=webhook_secret,
        path='/webhook2'
    )

if __name__ == '__main__':
    logger.info("Бот успешно запущен")
    asyncio.run(main())
