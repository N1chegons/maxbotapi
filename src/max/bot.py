import asyncio
import logging
import os
import datetime

import aiofiles
import aiohttp
import magic
import subprocess

from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import Command
from maxapi.types import MessageCreated, BotStarted, CallbackButton, InputMedia, LinkButton, \
    RequestContactButton, MessageCallback
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.admin.repository import AdminService

from src.config import settings
from src.max.models import UserState, MemoryMode, SubsStatus
from src.max.utils import upload_to_s3
from src.tochka_api.service import TochkaApiService
from src.yandexai.config import THEMES_INDEXES
from src.yandexai.orchestrator import ask_ai_with_index

logging.basicConfig(level=logging.INFO)
TOKEN = settings.MAX_BOT_TOKEN

bot = Bot(TOKEN)
dp = Dispatcher()

from src.max.repository import MaxService, AudioService

# Command
@dp.message_created(Command('new'))
async def new_session(event: MessageCreated):
    user_id = event.message.sender.user_id
    await MaxService.delete_session(user_id)
    await MaxService.create_session(user_id)
    await MaxService.update_user_state(user_id, UserState.NEW)

    reply_kb = InlineKeyboardBuilder()
    reply_kb.row(
        CallbackButton(
            text="Продолжить >",
            payload="continue"
        ),
    )

    await bot.send_message(
        user_id=user_id,
        text=(
            "Привет 👋 "
            "Я — Бот психолога Игоря Неповинных.\n\n"
            "Не «ещё один GPT», а цифровой Игорь, обученный на 15 годах практики, двух его книгах и 800+ видео.\n\n"
            "❗ Прежде чем начнём — пара важных вещей. Займёт минуту."
        ),
        attachments=[reply_kb.as_markup()]
    )

@dp.message_created(Command('mem'))
async def mem_memory_choice(event: MessageCreated):
    user_id = event.message.sender.user_id
    session_user = await MaxService.get_session(user_id)

    if not session_user:
        await bot.send_message(
            user_id=user_id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )
    else:
        reply_kb = InlineKeyboardBuilder()
        reply_kb.row(
            CallbackButton(
                text="Без памяти",
                payload="mem_memory_none"
            ),
            CallbackButton(
                text="Один диалог",
                payload="mem_memory_dialog"
            ),
            CallbackButton(
                text="Вся память",
                payload="mem_memory_full"
            ),
        )

        await bot.send_message(
            user_id=user_id,
            text=(
                "Скажи, что мы будет делать с твоими сообщениями?\n\n"
                "➖ Без памяти — каждая сессия с чистого листа, ничего не сохраняю. Максимум приватности, но минимум персонализации.\n\n"
                "➗ Память в рамках диалога — помню контекст, пока ты не скажешь «забудь». Потом стираю.\n\n"
                "➕ Вся память — помню всё, что ты мне говорил. Так я могу работать с тобой глубоко и замечать паттерны. Ты в любой момент можешь стереть всё командой - /mem.\n\n"
                "👉 Важно: на твоём гаджете сообщения останутся, удаляю с сервера. Выбирай."
            ),
            attachments=[reply_kb.as_markup()]
        )

@dp.message_created(Command('del'))
async def delete_info(event: MessageCreated):
    user_id = event.message.sender.user_id
    session_user = await MaxService.get_session(user_id)

    if not session_user:
        await bot.send_message(
            user_id=user_id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )
    else:
        reply_kb = InlineKeyboardBuilder()
        reply_kb.row(
            CallbackButton(
                text="Да",
                payload="delete_agree"
            ),
            CallbackButton(
                text="Нет",
                payload="delete_disagree"
            ),
        )

        await bot.send_message(
            user_id=user_id,
            text=(
                "Ты хочешь удалить всю информацию о себе?"
            ),
            attachments=[reply_kb.as_markup()]
        )

@dp.message_created(Command('end'))
async def closed_session(event: MessageCreated):
    user_id = event.message.sender.user_id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    if not session_user:
        await bot.send_message(
            user_id=user_id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )
    else:
        history = await MaxService.get_history(user_id)

        selected_topic = "Консультации"
        index_id = THEMES_INDEXES.get(selected_topic)
        text = f"""
            ПРОМТ для команды /end
                Процесс подведения итогов:
                1. Проанализируй все сообщения пользователя
                2. Перечисли основные темы, которые вы обсудили.
                3. Попроси пользователя выбрать самую важную тему: Подумай, какая тема вызвала у тебя больше всего эмоций. Или две.»
                4. Ещё раз проанализируй все сообщения, которые связаны с выбранной темой.
                5. Сделай короткие выводы и напомни результаты от изменения поведения пользователя.
                
            Вот все сообщения пользоватля:
            {history}
            """

        answer = ask_ai_with_index(index_id, text, selected_topic, history)

        if user.memory_mode == MemoryMode.session:
            await MaxService.delete_messages(user.user_id)
            await bot.send_message(
                user_id=user_id,
                text=answer
            )
        elif user.memory_mode == MemoryMode.full:
            await bot.send_message(
            user_id=user_id,
                text=answer
            )
        else:
            await bot.send_message(
            user_id=user_id,
                text="Данные не найдены.\nИзмените тип памяти при помощи /mem"
            )

@dp.message_created(Command('help'))
async def instruction(event: MessageCreated):
    user_id = event.message.sender.user_id

    reply_kb = InlineKeyboardBuilder()
    reply_kb.row(
        LinkButton(
            text="про Бота >",
            url="https://disk.yandex.ru/i/AHiHqufv2KT9bQ"
        )
    )

    await bot.send_message(
        user_id=user_id,
        text=(
            "📋 **Что я умею:**\n\n"
            "🔁 /new — начать всё заново, очистить текущую сессию\n"
            "🧠 /mem — выбрать, сколько я буду помнить (всё / диалог / ничего) + короткое видео\n"
            "💀 /del — полностью удалить все твои данные (без возможности восстановления)\n"
            "❓ /help — частые вопросы и видео про меня\n"
            "💳 /sub — проверить подписку, продлить или оплатить\n"
            "📊 /end — я проанализирую наш диалог и напишу краткий итог\n"
            "📅 /igor — записаться на живую консультацию с Игорем + видео\n"
        ),
        attachments=[reply_kb.as_markup()]

    )

@dp.message_created(Command('igor'))
async def igor_command(event: MessageCreated):
    user_id = event.message.sender.user_id
    username = event.from_user.username
    session_user = await MaxService.get_session(user_id)

    if not session_user:
        await bot.send_message(
            user_id=user_id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    already_request = await MaxService.get_request(user_id)
    if already_request:
        await bot.send_message(
            user_id=user_id,
            text="✔️ Вы уже отправили заявку на консультацию!\n\nВы можете продолжить задавать вопросы."
        )

    else:
        reply_kb = InlineKeyboardBuilder()
        reply_kb.row(
            LinkButton(
                text="про Эксперта >",
                url="https://disk.yandex.ru/i/b0q0Vt9a3M7cMg"
            ),
            CallbackButton(text="✅ ДА", payload="consult_agree"),
            CallbackButton(text="❌ НЕТ", payload="consult_disagree"),
        )

        await bot.send_message(
        user_id=user_id,
        text=(
            "Подумай ещё раз...\n"
            "Игорь берёт не всех и не каждого.\n"
            "Я сохраню последние двадцать сообщений: передам их Игорю.\n"
            "Он оценит качество гипотезы и напишет тебе.\n\n"
            "Ты уверен?(Выбери ДА/НЕТ)"
        ),
        attachments=[reply_kb.as_markup()]
    )

@dp.message_created(Command('sub'))
async def show_subscription_info(event: MessageCreated):
    user_id = event.from_user.user_id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    if not user:
        await bot.send_message(
            user_id=user_id,
            text="❌ Пользователь не найден. Напишите /new"
        )
        return

    now = datetime.datetime.now(datetime.UTC)
    is_active = False
    next_payment_date = None
    status_text = ""

    # 1. Активная подписка
    if user.subscription_status == SubsStatus.active and user.subscription_ends_at:
        if user.subscription_ends_at > now:
            is_active = True
            next_payment_date = user.subscription_ends_at
            status_text = "✅ Активна"
        else:
            status_text = "❌ Истекла"

    # 2. Льготный период
    elif user.subscription_status == SubsStatus.grace_period and user.subscription_ends_at:
        if user.subscription_ends_at > now:
            is_active = True
            next_payment_date = user.subscription_ends_at
            status_text = "⚠️ Льготный период (попытка списания)"
        else:
            status_text = "❌ Истекла"

    # 3. Отменённая, но ещё действующая
    elif user.subscription_status == SubsStatus.cancelled and user.subscription_ends_at:
        if user.subscription_ends_at > now:
            is_active = True
            next_payment_date = user.subscription_ends_at
            status_text = "⏸️ Отменена (доступ до даты)"
        else:
            status_text = "❌ Истекла"

    # 4. Триал
    elif user.subscription_status == SubsStatus.trial and user.trial_ends_at:
        if user.trial_ends_at > now:
            is_active = True
            next_payment_date = user.trial_ends_at
            status_text = "🧪 Пробный период"
        else:
            status_text = "❌ Триал истёк"

    # 5. Нет подписки
    else:
        status_text = "❌ Нет активной подписки"

    # Формируем сообщение
    text = f"💳 **Подписка**\n"
    text += f"📌 Статус: {status_text}\n"

    if next_payment_date:
        days_left = (next_payment_date - now).days
        text += f"📅 Следующее списание: {next_payment_date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Осталось дней: {days_left}\n"

    text += f"💰 Тариф: Базовый (650 ₽/мес)\n\n"

    # Кнопки
    kb = InlineKeyboardBuilder()


    if is_active:
        kb.row(CallbackButton(text="❌ Отменить подписку", payload="cancel_subscription"))
    else:
        if user.has_started_subscription:
            payment_data = TochkaApiService().create_payment_link(650, user_id=user_id, platform="MAX")
            kb.row(LinkButton(text="💳 Оплатить 650 ₽", url=payment_data["payment_link"]))
            await TochkaApiService.save_payment(
                user_id=user_id,
                operation_id=payment_data["payment_id"],
                amount=650.00
            )
        else:
            payment_data = TochkaApiService().create_payment_link(14, user_id=user_id, platform="MAX")
            kb.row(LinkButton(text="💳 Стартовая подписка 14 ₽", url=payment_data["payment_link"]))
            await TochkaApiService.save_payment(
                user_id=user_id,
                operation_id=payment_data["payment_id"],
                amount=14.00
            )

    await bot.send_message(
        user_id=user_id,
        text=text,
        attachments=[kb.as_markup()]
    )

# admin
@dp.message_created(Command('admin'))
async def admin_panel(event: MessageCreated):
    user_id = event.message.sender.user_id
    if not AdminService.is_admin(user_id):
        await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
        return

    text = (
        "👋 **Добро пожаловать в админ-панель!**\n\n"
        "📊 **Доступные команды:**\n\n"
        "🔹 /st [дни] - просмотр статистки за кол-во дней(по умолчанию 1)\n"
        "🔹 /con — посмотреть заявки на консультацию\n"
        "🔹 /ha — помощь по командам\n\n"
    )

    await bot.send_message(user_id=user_id, text=text)

@dp.message_created(Command('st'))
async def stats_command(event: MessageCreated):
    user_id = event.message.sender.user_id
    if not AdminService.is_admin(user_id):
        await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
        return

    parts = event.message.body.text.split()
    days = 1

    if len(parts) > 1:
        try:
            days = int(parts[1])
            if days < 1:
                days = 1
            if days > 365:
                days = 365
        except ValueError:
            await bot.send_message(user_id=user_id, text="❌ Неверный формат. Используйте: `/stats [дни]`")
            return

    count_message = await AdminService.get_total_messages_last_days_admin()

    report = f"📊 **Всего сообщений за {days} дн.: {count_message}**\n"

    await bot.send_message(user_id=user_id, text=report)

@dp.message_created(Command('con'))
async def view_appointment(event: MessageCreated):
    user_id = event.message.sender.user_id
    if not AdminService.is_admin(user_id):
        await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
        return

    parts = event.message.body.text.split()

    if len(parts) >= 2:
        try:
            app_id = int(parts[1])
        except ValueError:
            await bot.send_message(user_id=user_id, text="❌ Неверный формат. Используйте: /con <id>(порядковый номер записи)")
            return

        request = await MaxService.get_request_by_id(app_id)
        if not request:
            await bot.send_message(user_id=user_id, text=f"❌ Заявка с ID {app_id} не найдена")
            return

        await MaxService.mark_request_viewed(app_id)

        md_content = f"# 📋 Консультация #{request.id}\n\n"
        md_content += f"Клиент: {request.client_id}\n"
        md_content += f"Контакт: {request.contact}\n"
        md_content += f"Запись на: {request.appointment_date.strftime('%d.%m.%Y %H:%M')}\n"
        md_content += f"Дата подачи заявки: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        md_content += "---\n\n"
        md_content += "## 💬 Последние сообщения\n\n"
        md_content += request.messages if request.messages else "Нет сохранённых сообщений"

        filename = f"consultation_{request.client_id}.md"
        async with aiofiles.open(filename, "w", encoding='utf-8') as f:
            await f.write(md_content)

        await bot.send_message(
            user_id=user_id,
            text=f"📋 Консультация #{request.id}",
            attachments=[
                InputMedia(
                    path=filename,
                )
            ]
        )

        os.remove(filename)

    else:
        appointments = await MaxService.get_unviewed_request()

        if not appointments:
            await bot.send_message(user_id=user_id, text="Нет новых заявок на консультацию")
            return

        text = "📋 **Заявки на консультацию:**\n\n"
        for app in appointments:
            status = "✅" if app.viewed else "🆕"
            text += f"{status} id:{app.id} — {app.appointment_date.strftime('%d.%m.%Y 20:00')} — {app.contact}\n"

        text += "\n📝 Для просмотра деталей: /con <id>(порядковый номер записи)"

        await bot.send_message(user_id=user_id, text=text)

@dp.message_created(Command('ha'))
async def admin_help_command(event: MessageCreated):
    user_id = event.message.sender.user_id

    if not AdminService.is_admin(user_id):
        await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
        return

    text = (
        "👋 **Добро пожаловать в админ-панель!**\n\n"
        "📊 **Доступные команды:**\n\n"
        "🔹 /st [дни] - просмотр статистки за кол-во дней(по умолчанию 1)\n"
        "🔹 /con — посмотреть заявки на консультацию\n"
        "🔹 /ha — помощь по командам\n\n"
    )

    await bot.send_message(user_id=user_id, text=text)


# logic
@dp.bot_started()
async def bot_started(event: BotStarted):
    user_id = event.user.user_id
    user = await MaxService.get_user(user_id)

    if not user:
        await MaxService.create_user(user_id, "MAX")
        await MaxService.create_session(user_id)

        reply_kb = InlineKeyboardBuilder()
        reply_kb.row(
            CallbackButton(
                text="Продолжить >",
                payload="continue"
            ),
        )

        await bot.send_message(
            user_id=user_id,
            text=(
                "Привет 👋 "
                "Я — Бот психолога Игоря Неповинных.\n\n"
                "Не «ещё один GPT», а цифровой Игорь, обученный на 15 годах практики, двух его книгах и 800+ видео.\n\n"
                "❗ Прежде чем начнём — пара важных вещей."
                " Займёт минуту."
            ),
            attachments=[reply_kb.as_markup()]
        )
    else:
        await bot.send_message(
            user_id=user_id,
            text="Привет 👋"
                 "Ты уже зарегестрирован.\n\n"
                 "Если хочешь начать все сначала пиши - /new"
        )

@dp.message_callback(F.callback.payload == "delete_agree")
async def handle_continue(callback: MessageCallback):
    user_id = callback.callback.user.user_id

    await MaxService.delete_session(user_id)
    await MaxService.create_session(user_id)

    await callback.message.edit(
        text="Все данные удалены. Начинай снова /new",
        attachments=[]
    )

@dp.message_callback(F.callback.payload == "delete_disagree")
async def handle_continue(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    await callback.message.edit(
        text="Давай продолжим. На чём мы остановились",
        attachments=[]
    )

@dp.message_callback(F.callback.payload == "continue")
async def handle_continue(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    user = await MaxService.get_user(user_id)
    await MaxService.update_user_state(user_id, UserState.ONBOARDING_DISCLAIMER)


    reply_kb = InlineKeyboardBuilder()
    reply_kb.row(
        CallbackButton(
            text="Конечно согласен",
            payload="agree"
        ),
        CallbackButton(
            text="Не согласен",
            payload="disagree"
        ),
    )

    await callback.message.edit(
        text=(
            "Я не врач и не психотерапевт.\n"
            "Я не ставлю диагнозы и не лечу.\n"
            "Кризисные ситуации - не ко мне (суицид, насилие в семье, острая боль).\n\n"
            "Я успокою голову и сделаю тебя сильным. Согласен❓\n\nТогда давай знакомиться 😎"
        ),
        attachments=[reply_kb.as_markup()]
    )

@dp.message_callback(F.callback.payload == "disagree")
async def handle_disagree(callback: MessageCallback):
    await callback.message.edit(
        text=(
            "Понял. Возвращайся, если передумаешь"
        ), attachments=[]
    )

@dp.message_callback(F.callback.payload == "agree")
async def handle_agree(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    await MaxService.update_user_state(user_id, UserState.ONBOARDING_MENU)

    reply_kb = InlineKeyboardBuilder()
    reply_kb.row(
        CallbackButton(
            text="Запрос >",
            payload="query"
        ),
        LinkButton(
            text="про Бота >",
            url="https://disk.yandex.ru/i/AHiHqufv2KT9bQ"
        ),
        LinkButton(
            text="про Эксперта >",
            url="https://disk.yandex.ru/i/b0q0Vt9a3M7cMg"
        ),
    )
    await callback.message.edit(
        text=(
            "Отлично. Что хочешь дальше?\n\nВыбирай❗"
        ),
        attachments = [reply_kb.as_markup()]
    )

@dp.message_callback(F.callback.payload == "query")
async def handle_query(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    user = await MaxService.get_user(user_id)

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    reply_kb = InlineKeyboardBuilder()
    reply_kb.row(
        CallbackButton(
            text="Без памяти",
            payload="memory_none"
        ),
        CallbackButton(
            text="Один диалог",
            payload="memory_dialog"
        ),
        CallbackButton(
            text="Вся память",
            payload="memory_full"
        ),
    )

    await callback.message.edit(
        text=(
            "Скажи, что мы будет делать с твоими сообщениями?\n\n"
            "➖ Без памяти — каждая сессия с чистого листа, ничего не сохраняю. Максимум приватности, но минимум персонализации.\n\n"
            "➗ Память в рамках диалога — помню контекст, пока ты не скажешь «забудь». Потом стираю.\n\n"
            "➕ Вся память — помню всё, что ты мне говорил. Так я могу работать с тобой глубоко и замечать паттерны. Ты в любой момент можешь стереть всё командой - /mem.\n\n"
            "👉 Важно: на твоём гаджете сообщения останутся, удаляю с сервера. Выбирай."
        ),
        attachments=[reply_kb.as_markup()]
    )

async def handle_agree_subs(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    payment_data = TochkaApiService().create_payment_link(14, user_id=user_id, platform="MAX")

    if not payment_data or not payment_data.get("payment_link"):
        await callback.message.answer()
        await callback.message.edit(
            text="❌ Ошибка при создании платежа. Попробуйте позже."
        )
        return

    await TochkaApiService.save_payment(
        user_id=user_id,
        operation_id=payment_data["payment_id"],
        amount=14.00
    )

    kb = InlineKeyboardBuilder()
    kb.row(LinkButton(text="💳 14 рублей за 14 дней теста", url=payment_data["payment_link"]))
    kb.row(LinkButton(text="Изучить сайт", url="https://psy.nepovinnyh.ru"))

    await callback.message.answer(
        text=(
            "Ты посмотрел видео и выбрал память. Оцени свой уровень доверия ⚠️ Если информации недостаточно, изучи сайт👇 Сначала тест, потом автоматические списания по 650р каждый месяц ❗️ Если что-то не понял и хочешь вернуться назад, напиши /new"
        ),
        attachments=[kb.as_markup()]
    )

    await callback.message.answer(
        text=(
            "После оплаты 14 рублей начнётся консультация."
        )
    )
async def show_chat(user_id: int):
    await bot.send_message(
        user_id=user_id,
        text="Расскажи (текст или аудио), что тебя беспокоит прямо сейчас.\nДля начала нам нужна та эмоция, которая актуальна в данный момент. Что ты чувствуешь? Что переживаешь?",
    )
async def send_video(callback: MessageCallback):
    video = InputMedia(path="video_cache/04.mp4")
    await callback.message.edit(
        text="",
        attachments=[video]
    )


@dp.message_callback(F.callback.payload == "memory_none")
async def handle_memory_none(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    user = await MaxService.get_user(user_id)

    await MaxService.update_memory_mode(user_id, MemoryMode.none)

    await callback.answer()
    await callback.message.edit(
            text="🎬 Видео загружается, секунду...",
            attachments=[]
        )

    asyncio.create_task(send_video(callback))

    await asyncio.sleep(10)
    if user.has_started_subscription:
        await show_chat(user.user_id)
    else:
        await handle_agree_subs(callback)
@dp.message_callback(F.callback.payload == "mem_memory_none")
async def handle_mem_memory_none(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    await MaxService.update_memory_mode(user_id, MemoryMode.none)

    await callback.message.edit(
        text='Выбор памяти изменен на "Без памяти"\n\nМожете продолжить диалог.',
        attachments=[]
    )

@dp.message_callback(F.callback.payload == "memory_dialog")
async def handle_memory_dialog(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    user = await MaxService.get_user(user_id)

    await MaxService.update_memory_mode(user_id, MemoryMode.session)

    await callback.answer()
    await callback.message.edit(
        text="🎬 Видео загружается, секунду...",
        attachments=[]
    )

    asyncio.create_task(send_video(callback))

    await asyncio.sleep(10)
    if user.has_started_subscription:
        await show_chat(user.user_id)
    else:
        await handle_agree_subs(callback)

@dp.message_callback(F.callback.payload == "mem_memory_dialog")
async def handle_mem_memory_none(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    await MaxService.update_memory_mode(user_id, MemoryMode.session)

    await callback.message.edit(
        text='Выбор памяти изменен на "Один диалог"\n\nМожете продолжить диалог.',
        attachments=[]
    )

@dp.message_callback(F.callback.payload == "memory_full")
async def handle_memory_full(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    user = await MaxService.get_user(user_id)

    await MaxService.update_memory_mode(user_id, MemoryMode.full)

    await callback.answer()
    await callback.message.edit(
        text="🎬 Видео загружается, секунду...",
        attachments=[]
    )

    asyncio.create_task(send_video(callback))

    await asyncio.sleep(10)
    if user.has_started_subscription:
        await show_chat(user.user_id)
    else:
        await handle_agree_subs(callback)

@dp.message_callback(F.callback.payload == "mem_memory_full")
async def handle_mem_memory_none(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    await MaxService.update_memory_mode(user_id, MemoryMode.full)

    await callback.message.edit(
        text='Выбор памяти изменен на "Вся память"\n\nМожете продолжить диалог.',
        attachments=[]
    )

@dp.message_callback(F.callback.payload == "consult_agree")
async def igor_confirm(callback: MessageCallback):
    user_id = callback.callback.user.user_id

    reply_kb = InlineKeyboardBuilder()
    reply_kb.row(
        RequestContactButton(
            text="📱 Поделиться номером"
        )
    )

    await callback.message.edit(
        text="Пожалуйста, поделись своим номером телефона, чтобы я мог записать тебя на консультацию.",
        attachments=[reply_kb.as_markup()]
    )

@dp.message_created(F.message.body.text)
async def handle_message(event: MessageCreated):
    text = event.message.body.text
    if text.startswith('/'):
        return

    user_id = event.message.sender.user_id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    if not session_user:
        await bot.send_message(
            user_id=user_id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    elif not await MaxService.can_send_message(user_id):
        await bot.send_message(
            user_id=user_id,
            text="🔒 Ваша подписка не активна.\nПожалуйста, оплатите доступ в /sub"
        )
        return

    else:
        selected_topic = "Консультации"
        index_id = THEMES_INDEXES.get(selected_topic)
        history = await MaxService.get_history(user_id, limit=200)
        answer = ask_ai_with_index(index_id, text, selected_topic, history)

        if answer:
            if user.memory_mode != MemoryMode.none:
                last_exchange = f"Клиент: {text}\n\nБот: {answer}"
                await MaxService.add_message(user_id, session_user.id, "user", text)
                await MaxService.add_message(user_id, session_user.id, "assistant", answer)
            await bot.send_message(user_id=user_id, text=answer)
        else:
            await bot.send_message(
                user_id=user_id,
                text="⚠️ Не удалось получить ответ. Попробуйте позже."
            )

@dp.message_created(F.message.body.attachments[0].type == 'contact')
async def handle_contact(event: MessageCreated):
    user_id = event.message.sender.user_id

    contact = event.message.body.attachments[0].payload
    vcf = contact.vcf_info
    phone = vcf.split('TEL;TYPE=cell:')[1].split('\n')[0]

    history = await MaxService.get_last_messages(user_id, limit=20)
    history_text = "\n".join([
        f"{'🧑 Клиент' if msg.role == 'user' else '🤖 Бот'}: {msg.content}"
        for msg in history
    ])

    appointment_date = await MaxService.get_next_free_date()

    await MaxService.add_request(
        client_id=user_id,
        contact=phone,
        messages=history_text,
        appointment_date=appointment_date
    )

    await bot.send_message(
        user_id=event.from_user.user_id,
        text="✅ Спасибо! Игорь свяжется с вами для подтверждения консультации.\n\n"
             "Вы можете продолжить вести диалог.",
    )

@dp.message_created(F.message.body.attachments)
async def handle_voice_message(event: MessageCreated):
    user_id = event.message.sender.user_id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    if not session_user:
        await bot.send_message(
            user_id=user_id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    elif not await MaxService.can_send_message(user_id):
        await bot.send_message(
            user_id=user_id,
            text="🔒 Ваша подписка не активна.\nПожалуйста, оплатите доступ в /sub"
        )
        return

    else:
        selected_topic = "Консультации"
        index_id = THEMES_INDEXES.get(selected_topic)
        history = await MaxService.get_history(user_id, limit=200)


        audio_attachment = None
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
                if user.memory_mode != MemoryMode.none:
                    last_exchange = f"Клиент: {recognized_text}\n\nБот: {answer}"
                    await MaxService.add_message(user_id, session_user.id, "user", recognized_text)
                    await MaxService.add_message(user_id, session_user.id, "assistant", answer)
                await bot.send_message(user_id=user_id, text=answer)
            else:
                await bot.send_message(
                    user_id=user_id,
                    text="⚠️ Не удалось получить ответ. Попробуйте позже."
                )

        except Exception as e:
            print(f"Ошибка: {e}")
            await bot.send_message(user_id=user_id, text="⚠️ Ошибка обработки голосового. Попробуйте текстом.")


async def main():
    webhook_url = "https://bot.nepovinnyh.ru/webhook"
    webhook_secret = settings.SECRET_WEBHOOK_KEY

    # Регистрируем новую на поддомен
    await bot.subscribe_webhook(url=webhook_url, secret=webhook_secret)

    await dp.handle_webhook(
        bot=bot,
        host='0.0.0.0',
        port=8080,
        secret=webhook_secret,
        path='/webhook'
    )

if __name__ == '__main__':
    asyncio.run(main())

