import asyncio
import logging
import os
import aiofiles
import requests
import telebot
from aiohttp import web

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, \
    KeyboardButton
from telebot.async_telebot import AsyncTeleBot

from src.max.models import UserState, MemoryMode
from src.admin.repository import AdminService
from src.max.repository import MaxService, AudioService
from src.max.utils import upload_to_s3
from src.tochka_api.service import TochkaApiService
from src.yandexai.config import THEMES_INDEXES
from src.yandexai.orchestrator import ask_ai_with_index
from src.config import settings

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
WEBHOOK_PATH = "/tg_webhook"
WEBHOOK_URL = f"https://bot.nepovinnyh.ru{WEBHOOK_PATH}"

app = web.Application()
bot = AsyncTeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
async def start(message):
    user_id = message.from_user.id
    user = await MaxService.get_user(user_id)

    if not user:
        await MaxService.create_user(user_id, "TELEGRAM")
        await MaxService.create_session(user_id)

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(text="Продолжить >", callback_data="continue"))

        await bot.send_message(
            chat_id=message.chat.id,
            text="Привет 👋 "
            "Я — Бот психолога Игоря Неповинных.\n\n"
            "Не «ещё один GPT», а цифровой Игорь, обученный на 15 годах практики, двух его книгах и 800+ видео.\n\n"
            "❗ Прежде чем начнём — пара важных вещей. Займёт минуту.",
            reply_markup=kb
        )
    else:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Привет 👋"
                 "Ты уже зарегестрирован.\n\n"
                 "Если хочешь начать все сначала пиши - /new"
        )

@bot.message_handler(commands=['new'])
async def new_session(message):
    user_id = message.from_user.id
    await MaxService.delete_session(user_id)
    await MaxService.create_session(user_id)
    await MaxService.update_user_state(user_id, UserState.NEW)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="Продолжить >", callback_data="continue"))

    await bot.send_message(
        chat_id=message.chat.id,
        text="Привет 👋 "
        "Я — Бот психолога Игоря Неповинных.\n\n"
        "Не «ещё один GPT», а цифровой Игорь, обученный на 15 годах практики, двух его книгах и 800+ видео.\n\n"
        "❗ Прежде чем начнём — пара важных вещей. Займёт минуту.",
        reply_markup=kb
    )

@bot.message_handler(commands=['mem'])
async def mem_memory_choice(message):
    user_id = message.from_user.id
    user_reg = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_reg.user_id)

    if not session_user:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(text="Без памяти", callback_data="mem_memory_none"),
        InlineKeyboardButton(text="Один диалог", callback_data="mem_memory_dialog"),
        InlineKeyboardButton(text="Вся память", callback_data="mem_memory_full")
    )

    await bot.send_message(
        chat_id=message.chat.id,
        text="Скажи, что мы будем делать с твоими сообщениями?\n\n"
        "➖ Без памяти — каждая сессия с чистого листа, ничего не сохраняю. Максимум приватности, но минимум персонализации.\n\n"
        "➗ Память в рамках диалога — помню контекст, пока ты не скажешь «забудь». Потом стираю.\n\n"
        "➕ Вся память — помню всё, что ты мне говорил. Так я могу работать с тобой глубоко и замечать паттерны. Ты в любой момент можешь стереть всё командой - /mem.\n\n"
        "👉 Важно: на твоём гаджете сообщения останутся, удаляю с сервера. Выбирай.",
        reply_markup=kb
    )

@bot.message_handler(commands=['del'])
async def delete_info(message):
    user_id = message.from_user.id
    session_user = await MaxService.get_session(user_id)

    if not session_user:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(text="Да", callback_data="delete_agree"),
        InlineKeyboardButton(text="Нет", callback_data="delete_disagree")
    )

    await bot.send_message(
        chat_id=message.chat.id,
        text="Ты хочешь удалить всю информацию о себе?",
        reply_markup=kb
    )

@bot.message_handler(commands=['end'])
async def closed_session(message):
    user_id = message.from_user.id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    if not session_user:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )
    else:
        history = await MaxService.get_history(user_id)

        selected_topic = "Консультации"
        index_id = THEMES_INDEXES.get(selected_topic)
        text = f"""
               Подведи итог этого диалога в строгом формате:
    
               Что мы сегодня разобрали:
               • [пункт 1]
               • [пункт 2]
               • [пункт 3]
    
               Что я зафиксировал:
               [одна ключевая фраза-инсайт]
    
               Куда двинуться дальше:
               • [вариант 1]
               • [вариант 2]
    
               Вот диалог:
               {history}
               """

        answer = ask_ai_with_index(index_id, text, selected_topic, history)

        if user.memory_mode == MemoryMode.session:
            await MaxService.delete_messages(user_id)
            await bot.send_message(
                chat_id=message.chat.id,
                text=answer
            )
        elif user.memory_mode == MemoryMode.full:
            await bot.send_message(
                chat_id=message.chat.id,
                text=answer
            )
        else:
            await bot.send_message(
                chat_id=message.chat.id,
                text="Данные не найдены.\nИзмените тип памяти при помощи /mem"
            )

@bot.message_handler(commands=['help'])
async def instruction(message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="про Бота >", url="https://disk.yandex.ru/i/AHiHqufv2KT9bQ"))

    await bot.send_message(
            chat_id=message.chat.id,
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
            reply_markup=kb

        )

@bot.message_handler(commands=['igor'])
async def igor_command(message):
    user_id = message.from_user.id
    session_user = await MaxService.get_session(user_id)

    if not session_user:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    # await AdminService.log_command_admin(user_id, "/igor")

    already_request = await MaxService.get_request(user_id)
    if already_request:
        await bot.send_message(
            chat_id=message.chat.id,
            text="✔️ Вы уже отправили заявку на консультацию!\n\nВы можете продолжить задавать вопросы."
        )

    else:
        kb = InlineKeyboardMarkup()
        kb.add(
        InlineKeyboardButton(text="Да", callback_data="consult_agree"),
            InlineKeyboardButton(text="Нет", callback_data="consult_disagree")
        )
        kb.add(InlineKeyboardButton(text="про Эксперта >", url="https://disk.yandex.ru/i/b0q0Vt9a3M7cMg")),

        await bot.send_message(
            chat_id=message.chat.id,
            text=(
                "Подумай ещё раз...\n"
                "Игорь берёт не всех и не каждого.\n"
                "Я сохраню последние двадцать сообщений: передам их Игорю.\n"
                "Он оценит качество гипотезы и напишет тебе.\n\n"
                "Ты уверен?(Выбери ДА/НЕТ)"
            ),
            reply_markup=kb
        )


@bot.message_handler(commands=['admin'])
async def admin_panel(message):
    user_id = message.from_user.id
    if not AdminService.is_admin(user_id):
        await bot.send_message(chat_id=message.chat.id, text="⛔ Нет доступа")
        return

    text = (
        "👋 **Добро пожаловать в админ-панель!**\n\n"
        "📊 **Доступные команды:**\n\n"
        "🔹 /st [дни] - просмотр статистки за кол-во дней(по умолчанию 1)\n"
        "🔹 /con — посмотреть заявки на консультацию\n"
        "🔹 /ha — помощь по командам\n\n"
    )

    await bot.send_message(chat_id=message.chat.id, text=text)

@bot.message_handler(commands=['st'])
async def stats_command(message):
    user_id = message.from_user.id
    if not AdminService.is_admin(user_id):
        await bot.send_message(chat_id=message.chat.id, text="⛔ Нет доступа")
        return

    parts = message.text.split()
    days = 1

    if len(parts) > 1:
        try:
            days = int(parts[1])
            if days < 1:
                days = 1
            if days > 365:
                days = 365
        except ValueError:
            await bot.send_message(chat_id=message.chat.id, text="❌ Неверный формат. Используйте: `/stats [дни]`")
            return

    count_message = await AdminService.get_total_messages_last_days_admin()

    report = f"📊 **Всего сообщений за {days} дн.: {count_message}**\n"

    await bot.send_message(chat_id=message.chat.id, text=report)

@bot.message_handler(commands=['con'])
async def view_appointment(message):
    user_id = message.from_user.id
    if not AdminService.is_admin(user_id):
        await bot.send_message(chat_id=message.chat.id, text="⛔ Нет доступа")
        return

    parts = message.text.split()

    if len(parts) >= 2:
        try:
            app_id = int(parts[1])
        except ValueError:
            await bot.send_message(chat_id=message.chat.id,
                                   text="❌ Неверный формат. Используйте: /con <id>(порядковый номер записи)")
            return

        request = await MaxService.get_request_by_id(app_id)
        if not request:
            await bot.send_message(chat_id=message.chat.id, text=f"❌ Заявка с ID {app_id} не найдена")
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

        filename = f"consultation_{request.client_id}.txt"
        async with aiofiles.open(filename, "w", encoding='utf-8') as f:
            await f.write(md_content)
        with open(filename, "rb") as f:
            await bot.send_document(chat_id=message.chat.id, document=f, caption=f"📋 Консультация #{request.id}")

        os.remove(filename)

    else:
        appointments = await MaxService.get_unviewed_request()

        if not appointments:
            await bot.send_message(chat_id=message.chat.id, text="Нет новых заявок на консультацию")
            return

        text = "📋 **Заявки на консультацию:**\n\n"
        for apps in appointments:
            status = "✅" if apps.viewed else "🆕"
            text += f"{status} id:{apps.id} — {apps.appointment_date.strftime('%d.%m.%Y 20:00')} — {apps.contact}\n"

        text += "\n📝 Для просмотра деталей: /con <id>(порядковый номер записи)"

        await bot.send_message(chat_id=message.chat.id, text=text)

@bot.message_handler(commands=['ha'])
async def admin_help_command(message):
    user_id = message.from_user.id
    if not AdminService.is_admin(user_id):
        await bot.send_message(chat_id=message.chat.id, text="⛔ Нет доступа")
        return

    text = (
        "👋 **Добро пожаловать в админ-панель!**\n\n"
        "📊 **Доступные команды:**\n\n"
        "🔹 /st [дни] - просмотр статистки за кол-во дней(по умолчанию 1)\n"
        "🔹 /con — посмотреть заявки на консультацию\n"
        "🔹 /ha — помощь по командам\n\n"
    )

    await bot.send_message(chat_id=message.chat.id, text=text)

# logic
@bot.callback_query_handler(func=lambda call: call.data == "delete_agree")
async def handle_delete_info_agree(call: CallbackQuery):
    user_id = call.from_user.id
    await MaxService.delete_session(user_id)
    await MaxService.create_session(user_id)

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Все данные удалены. Начинай снова /new"
    )

@bot.callback_query_handler(func=lambda call: call.data == "delete_disagree")
async def handle_delete_info_disagree(call: CallbackQuery):
    await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Давай продолжим. На чём мы остановились"
        )

@bot.callback_query_handler(func=lambda call: call.data == "continue")
async def handle_continue(call: CallbackQuery):
    user_id = call.from_user.id
    await MaxService.update_user_state(user_id, UserState.ONBOARDING_DISCLAIMER)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(text="Конечно согласен", callback_data="agree"),
        InlineKeyboardButton(text="Не согласен", callback_data="disagree")
    )

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Я не врач и не психотерапевт.\n"
        "Я не ставлю диагнозы и не лечу.\n"
        "Кризисные ситуации - не ко мне (суицид, насилие в семье, острая боль).\n\n"
        "Я успокою голову и сделаю тебя сильным. Согласен❓\n\nТогда давай знакомиться 😎",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "disagree")
async def handle_disagree(call: CallbackQuery):
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    text="Понял. Возвращайся, если передумаешь"
    )

@bot.callback_query_handler(func=lambda call: call.data == "agree")
async def handle_agree(call: CallbackQuery):
    user_id = call.from_user.id
    await MaxService.update_user_state(user_id, UserState.ONBOARDING_MENU)

    user = await MaxService.get_user(user_id)

    if user and user.state != UserState.TRIAL_ACTIVE:
        await MaxService.start_trial(user_id)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="Запрос >", callback_data="query"),
    InlineKeyboardButton(text="про Бота >", url="https://disk.yandex.ru/i/AHiHqufv2KT9bQ"),
    InlineKeyboardButton(text="про Эксперта >", url="https://disk.yandex.ru/i/b0q0Vt9a3M7cMg"))

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Отлично. Что хочешь дальше?\n\nВыбирай❗",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "query")
async def handle_query(call: CallbackQuery):
    user_id = call.from_user.id
    user = await MaxService.get_user(user_id)

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(text="Без памяти", callback_data="memory_none"),
        InlineKeyboardButton(text="Один диалог", callback_data="memory_dialog"),
        InlineKeyboardButton(text="Вся память", callback_data="memory_full")
    )

    await bot.edit_message_text(
        "Скажи, что мы будем делать с твоими сообщениями?\n\n"
        "➖ Без памяти — каждая сессия с чистого листа, ничего не сохраняю. Максимум приватности, но минимум персонализации.\n\n"
        "➗ Память в рамках диалога — помню контекст, пока ты не скажешь «забудь». Потом стираю.\n\n"
        "➕ Вся память — помню всё, что ты мне говорил. Так я могу работать с тобой глубоко и замечать паттерны. Ты в любой момент можешь стереть всё командой - /mem.\n\n"
        "👉 Важно: на твоём гаджете сообщения останутся, удаляю с сервера. Выбирай.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb
    )

async def handle_agree_subs(call: CallbackQuery):
    user_id = call.from_user.id
    payment_data = TochkaApiService().create_payment_link(14, user_id=user_id)

    if not payment_data or not payment_data.get("payment_link"):
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="❌ Ошибка при создании платежа. Попробуйте позже."
        )
        return

    await TochkaApiService.save_payment(
        user_id=user_id,
        operation_id=payment_data["payment_id"],
        amount=14.00
    )

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="💳 14 рублей за 14 дней теста", url=payment_data["payment_link"]))
    kb.add(InlineKeyboardButton(text="Изучить сайт", url="https://psy.nepovinnyh.ru"))

    await bot.send_message(
        chat_id=call.message.chat.id,
        text=(
            "Ты посмотрел видео и выбрал память. Оцени свой уровень доверия ⚠️ Если информации недостаточно, изучи сайт👇 Сначала тест, потом автоматические списания по 650р каждый месяц ❗️ Если что-то не понял и хочешь вернуться назад, напиши /new"
        ),
        reply_markup=kb
    )
    await asyncio.sleep(2)
    await bot.send_message(
        chat_id=call.message.chat.id,
        text=(
            "После оплаты 14 рублей начнётся консультация."
        )
    )

async def show_chat_tg(user_id: int):
    await bot.send_message(
        chat_id=user_id,
        text="Расскажи (текст или аудио), что тебя беспокоит прямо сейчас.\n"
             "Для начала нам нужна та эмоция, которая актуальна в данный момент. "
             "Что ты чувствуешь? Что переживаешь?"
    )

@bot.callback_query_handler(func=lambda call: call.data == "memory_none")
async def handle_memory_none(call: CallbackQuery):
    user_id = call.from_user.id
    await MaxService.update_memory_mode(user_id, MemoryMode.none)
    user = await MaxService.get_user(user_id)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="видео", url="https://disk.yandex.ru/i/F8LpWWDviR-Erw"))

    await bot.edit_message_text(
        "Посмотри перед консультацией",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb
    )
    if user.has_started_subscription:
        await show_chat_tg(user_id)
    else:
        await handle_agree_subs(call)
@bot.callback_query_handler(func=lambda call: call.data == "mem_memory_none")
async def handle_mem_memory_none(call: CallbackQuery):
    user_id = call.from_user.id
    await MaxService.update_memory_mode(user_id, MemoryMode.none)

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text='Выбор памяти изменен на "Без памяти"\n\nМожете продолжить диалог.'
    )

@bot.callback_query_handler(func=lambda call: call.data == "memory_dialog")
async def handle_memory_dialog(call: CallbackQuery):
    user_id = call.from_user.id
    await MaxService.update_memory_mode(user_id, MemoryMode.session)
    user = await MaxService.get_user(user_id)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="видео", url="https://disk.yandex.ru/i/F8LpWWDviR-Erw"))

    await bot.edit_message_text(
        "Посмотри перед консультацией",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb
    )
    if user.has_started_subscription:
        await show_chat_tg(user_id)
    else:
        await handle_agree_subs(call)
@bot.callback_query_handler(func=lambda call: call.data == "mem_memory_dialog")
async def handle_mem_memory_dialog(call: CallbackQuery):
    user_id = call.from_user.id
    await MaxService.update_memory_mode(user_id, MemoryMode.session)

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text='Выбор памяти изменен на "Один диалог"\n\nМожете продолжить диалог.'
    )

@bot.callback_query_handler(func=lambda call: call.data == "memory_full")
async def handle_memory_full(call: CallbackQuery):
    user_id = call.from_user.id
    await MaxService.update_memory_mode(user_id, MemoryMode.full)
    user = await MaxService.get_user(user_id)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="видео", url="https://disk.yandex.ru/i/F8LpWWDviR-Erw"))

    await bot.edit_message_text(
        "Посмотри перед консультацией",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb
    )
    if user.has_started_subscription:
        await show_chat_tg(user_id)
    else:
        await handle_agree_subs(call)
@bot.callback_query_handler(func=lambda call: call.data == "mem_memory_full")
async def handle_mem_memory_full(call: CallbackQuery):
    user_id = call.from_user.id
    await MaxService.update_memory_mode(user_id, MemoryMode.session)

    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text='Выбор памяти изменен на "Вся память"\n\nМожете продолжить диалог.'
    )

@bot.callback_query_handler(func=lambda call: call.data == "consult_agree")
async def handle_consult_agree(call: CallbackQuery):
    await bot.delete_message(call.message.chat.id, call.message.message_id)

    contact_button = KeyboardButton(
        text="📱 Поделиться номером",
        request_contact=True
    )

    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )
    keyboard.add(contact_button)

    await bot.send_message(
        chat_id=call.message.chat.id,
        text="Пожалуйста, поделись своим номером телефона, чтобы я мог записать тебя на консультацию.",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "consult_disagree")
async def handle_consult_disagree(call: CallbackQuery):
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Ты отменил заявку на консультацию. Если хочешь записаться на консультацию - /igor"
    )



@bot.message_handler(content_types=['contact'])
async def handle_contact(message):
    contact = message.contact
    user_id = message.from_user.id

    phone = contact.phone_number
    name = contact.first_name

    history = await MaxService.get_last_messages(user_id, limit=200)
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
        chat_id=message.chat.id,
        text="✅ Спасибо! Игорь свяжется с вами для подтверждения консультации.\n\n"
                 "Вы можете продолжить вести диалог.",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )

@bot.message_handler(content_types=['voice'])
async def handle_voice(message):
    user_id = message.from_user.id
    user_reg = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)
    await MaxService.expire_trial_if_needed(user_id)

    if not session_user:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    elif user_reg.state == UserState.TRIAL_ENDED_NOT_PAID:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Извини, у тебя закончился пробный период. Сделай что-нибудь."
        )
        return

    else:
        selected_topic = "Консультации"
        index_id = THEMES_INDEXES.get(selected_topic)
        history = await MaxService.get_history(user_id, limit=200)
        file_info = await bot.get_file(message.voice.file_id)

        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        audio_data = requests.get(file_url).content

        s3_url = await upload_to_s3(audio_data)

        recognized_text = AudioService.recognize_from_s3(s3_url, settings.YC_API_KEY)

        answer = ask_ai_with_index(index_id, recognized_text, selected_topic, history)

        try:
            if answer:
                if user_reg.memory_mode != MemoryMode.none:
                    last_exchange = f"Клиент: {recognized_text}\n\nБот: {answer}"
                    await MaxService.add_message(user_id, session_user.id, "user", recognized_text)
                    await MaxService.add_message(user_id, session_user.id, "assistant", answer)
                await bot.send_message(chat_id=message.chat.id, text=answer)
            else:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="⚠️ Не удалось получить ответ. Попробуйте позже."
                )
        except Exception as e:
            print(f"Ошибка: {e}")
            await bot.send_message(chat_id=message.chat.id, text="⚠️ Ошибка обработки голосового. Попробуйте текстом.")

@bot.message_handler(func=lambda message: True)
async def handle_message(message):
    text = message.text
    if text.startswith('/'):
        return

    user_id = message.from_user.id
    user_reg = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)
    await MaxService.expire_trial_if_needed(user_id)

    if not session_user:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    elif user_reg.state == UserState.TRIAL_ENDED_NOT_PAID:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Извини, у тебя закончился пробный период. Сделай что-нибудь."
        )
        return

    else:
        selected_topic = "Консультации"
        index_id = THEMES_INDEXES.get(selected_topic)
        history = await MaxService.get_history(user_id, limit=200)
        answer = ask_ai_with_index(index_id, text, selected_topic, history)

        if answer:
            if user_reg.memory_mode != MemoryMode.none:
                last_exchange = f"Клиент: {text}\n\nБот: {answer}"
                await MaxService.add_message(user_id, session_user.id, "user", text)
                await MaxService.add_message(user_id, session_user.id, "assistant", answer)
            await bot.send_message(chat_id=message.chat.id, text=answer)
        else:
            await bot.send_message(
                chat_id=message.chat.id,
                text="⚠️ Не удалось получить ответ. Попробуйте позже."
            )


async def handle_webhook(request):
    try:
        body = await request.json()
        update = telebot.types.Update.de_json(body)
        await bot.process_new_updates([update])
        return web.Response(status=200, text="OK")
    except Exception as e:
        print(f"Ошибка: {e}")
        return web.Response(status=200, text="OK")
app.router.add_post(WEBHOOK_PATH, handle_webhook)
async def main():
    await bot.delete_webhook()
    await bot.set_webhook(url=WEBHOOK_URL)
    # Запускаем веб-сервер как асинхронную задачу
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='127.0.0.1', port=8081)
    await site.start()
    print(f"Бот запущен на http://127.0.0.1:8081{WEBHOOK_PATH}")
    # Бесконечно ждём
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())