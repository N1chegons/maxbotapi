import asyncio
import os
from typing import Any

import aiofiles
import requests
import telebot
from datetime import datetime
from aiohttp import web

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, \
    KeyboardButton
from telebot.async_telebot import AsyncTeleBot

from src.logger_config import setup_logger
from src.max.ending_sender import ending_session
from src.max.models import UserState, MemoryMode, SubsStatus
from src.admin.repository import AdminService
from src.max.utils import upload_to_s3
from src.tochka_api.service import TochkaApiService
from src.yandexai.config import THEMES_INDEXES
from src.yandexai.orchestrator import ask_ai_with_index
from src.config import settings

logger = setup_logger('telegram_bot', 'telegram', 'TELEGRAM_bot.log')
logger_admin = setup_logger('admin', 'admin', 'telegram_admin.log')

BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
WEBHOOK_PATH = "/tg_webhook"
WEBHOOK_URL = f"https://bot.nepovinnyh.ru{WEBHOOK_PATH}"

app = web.Application()
bot = AsyncTeleBot(BOT_TOKEN)

from src.max.repository import MaxService, AudioService

@bot.message_handler(commands=['start'])
async def start(message):
    user_id = message.from_user.id
    user = await MaxService.get_user(user_id)
    logger.info(f"Пользователь {user_id} запустил бота")

    if not user:
        await MaxService.create_user(user_id, "TELEGRAM")
        await MaxService.create_session(user_id)
        logger.info(f"Пользователь {user_id} успешно зарегестрировался")

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
        logger.info(f"Пользователь {user_id} уже зарегистрирован")
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
    logger.info(f"Смена памяти для пользователя {user_id}")

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
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
    kb.add(InlineKeyboardButton(text="про Память >", url="https://disk.yandex.ru/i/4N1TT70-vEuRwg"))

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
    logger.info(f"Удаление данных для пользователя {user_id}")

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
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
    if user.memory_mode != MemoryMode.none:
        await ending_session(user_id, user, "TELEGRAM")
    else:
        logger.info(f"Пользоватлеь {user_id} заканчивает диалог с памятью {MemoryMode.none}")
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
    logger.info(f"Запись на консультацию для пользователя {user_id}")

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        await bot.send_message(
            chat_id=message.chat.id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    already_request = await MaxService.get_request(user_id)
    if already_request:
        logger.info(f"Пользователь {user_id} уже записан на консультацию")
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

@bot.message_handler(commands=['bot'])
async def help_bot_command(message):
    user_id = message.from_user.id
    session_user = await MaxService.get_session(user_id)
    logger.info(f"Пользователь {user_id} отправил обращение")

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        await bot.send_message(
            chat_id=message.chat.id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    else:
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(text="✅ ОТПРАВИТЬ", callback_data="bot_send_problem"),
            InlineKeyboardButton(text="❌ ОТМЕНА", callback_data="bot_dsend"),
        )

        await bot.send_message(
            chat_id=message.chat.id,
            text=(
                "Если бот где-то затупил, то жми на кнопку отправить. Богдан разберётся 😉"
            ),
            reply_markup=kb
        )

async def create_payment_link(amount: float, user_id: int) -> Any | None:
    await asyncio.sleep(1)
    payment_data = TochkaApiService().create_payment_link(amount)
    logger.info(f"Создание ссылки на оплату для пользователя {user_id}")
    if payment_data and payment_data.get("payment_link"):
        logger.info(f"Платежная ссылка для пользователя {user_id} создана: {payment_data.get("payment_link")}")
        await TochkaApiService.save_payment(
            user_id=user_id,
            operation_id=payment_data["payment_id"],
            amount=amount
        )
        return payment_data["payment_link"]
    logger.warning(f"Не удалось создать платжную ссылку для пользователя {user_id}")
    return None
async def send_sub_buttons(user_id: int, user, message):
    kb = InlineKeyboardMarkup()

    if user.subscription_status in (SubsStatus.active, SubsStatus.grace_period):
        # noinspection PyDeprecation
        if user.subscription_ends_at and user.subscription_ends_at > datetime.utcnow():
            kb.add(InlineKeyboardButton(text="❌ Отменить подписку", callback_data="cancel_subscription"))
            await bot.send_message(chat_id=message.chat.id, text="🔧 Управление подпиской:", reply_markup=kb)
            return

    if user.has_started_subscription:
        payment_link = await create_payment_link(650.00, user_id)
        kb.row(InlineKeyboardButton(text="💳 Оплатить 650 ₽", url=payment_link))
    else:
        payment_link = await create_payment_link(14.00, user_id)
        kb.row(InlineKeyboardButton(text="💳 14 рублей за 14 дней теста", url=payment_link))

    await bot.send_message(chat_id=message.chat.id, text="Оплатите подписку:", reply_markup=kb)
async def get_subscription_status(user):
    # noinspection PyDeprecation
    now = datetime.utcnow()
    next_date = None

    if user.subscription_status in (SubsStatus.active, SubsStatus.grace_period):
        if user.subscription_ends_at and user.subscription_ends_at > now:
            next_date = user.subscription_ends_at
            status_text = "✅ Активна"
        else:
            status_text = "❌ Истекла"

    elif user.subscription_status == SubsStatus.trial:
        if user.trial_ends_at and user.trial_ends_at > now:
            next_date = user.trial_ends_at
            status_text = "🧪 Пробный период"
        else:
            status_text = "❌ Пробный период истёк"

    elif user.subscription_status == SubsStatus.cancelled:
        if user.subscription_ends_at and user.subscription_ends_at > now:
            next_date = user.subscription_ends_at
            status_text = "⏸ Отменена (доступ до даты)"
        else:
            status_text = "❌ Истекла"

    else:
        status_text = "❌ Нет активной подписки"

    return status_text, next_date

@bot.message_handler(commands=['sub'])
async def cmd_sub(message):
    user_id = message.from_user.id
    user = await MaxService.get_user(user_id)
    logger.info(f"Проверка подписки для пользователя {user_id}")

    if not user:
        logger.warning(f"Пользователь по {user_id} не найден")
        await bot.send_message(chat_id=message.chat.id, text="❌ Пользователь не найден. Напишите /start")
        return

    status_text, next_date = await get_subscription_status(user)

    text = f"💳 **Подписка**\n"
    text += f"📌 Статус: {status_text}\n"
    text += f"💰 Тариф: Базовый (650 ₽/мес)\n"
    if next_date:
        # noinspection PyDeprecation,PyUnresolvedReferences
        days_left = (next_date - datetime.utcnow()).days
        # noinspection PyUnresolvedReferences
        text += f"📅 Следующее списание: {next_date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Осталось дней: {days_left}\n"

    await bot.send_message(chat_id=message.chat.id, text=text)

    # Отправляем кнопки отдельным сообщением
    await send_sub_buttons(user_id, user, message)

# admin
@bot.message_handler(commands=['admin'])
async def admin_panel(message):
    user_id = message.from_user.id
    if not AdminService.is_admin(user_id):
        logger_admin.warning(f"Пользователь {user_id} не является админом")
        await bot.send_message(chat_id=message.chat.id, text="⛔ Нет доступа")
        return

    text = (
        "👋 **Добро пожаловать в админ-панель!**\n\n"
        "📊 **Доступные команды:**\n\n"
        "🔹 /st [дни] - просмотр статистки за кол-во дней(по умолчанию 1)\n"
        "🔹 /con — посмотреть заявки на консультацию\n"
        "🔹 /req — посмотреть обращения пользователей\n"
        "🔹 /ha — помощь по командам\n\n"
    )

    await bot.send_message(chat_id=message.chat.id, text=text)

@bot.message_handler(commands=['st'])
async def stats_command(message):
    user_id = message.from_user.id
    if not AdminService.is_admin(user_id):
        logger_admin.warning(f"Пользователь {user_id} не является админом")
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

    logger_admin.info(f"Админ {user_id} просмотрел статистику по сообщеиям за {count_message} дней")
    await bot.send_message(chat_id=message.chat.id, text=report)

@bot.message_handler(commands=['con'])
async def view_appointment(message):
    user_id = message.from_user.id
    if not AdminService.is_admin(user_id):
        logger_admin.warning(f"Пользователь {user_id} не является админом")
        await bot.send_message(chat_id=message.chat.id, text="⛔ Нет доступа")
        return

    parts = message.text.split()

    if len(parts) >= 2:
        try:
            app_id = int(parts[1])
        except ValueError:
            logger_admin.warning(f"Админ {user_id} ввел неверный формат для просмотра информации по консультации")
            await bot.send_message(chat_id=message.chat.id,
                                   text="❌ Неверный формат. Используйте: /con <id>(порядковый номер записи)")
            return

        request = await MaxService.get_request_by_id(app_id)
        if not request:
            logger_admin.warning(f"Консультация с id {app_id} не найдена")
            await bot.send_message(chat_id=message.chat.id, text=f"❌ Заявка с ID {app_id} не найдена")
            return

        await MaxService.mark_request_viewed(app_id)

        client_id = request.client_id or "Запрос с сайта"

        md_content = f"# 📋 Консультация #{request.id}\n\n"
        md_content += f"Клиент: {client_id}\n"
        md_content += f"Контакт: {request.contact}\n"
        md_content += f"Запись на: {request.appointment_date.strftime('%d.%m.%Y %H:%M')}\n"
        md_content += f"Дата подачи заявки: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        md_content += "---\n\n"
        md_content += "## 💬 Последние сообщения\n\n"
        md_content += request.messages if request.messages else "Нет сохранённых сообщений"

        filename = f"consultation_{request.client_id}.txt" if request.client_id else f"consultation_{request.created_at.strftime('%d_%m_%Y')}.txt"
        async with aiofiles.open(filename, "w", encoding='utf-8') as f:
            await f.write(md_content)
        with open(filename, "rb") as f:
            await bot.send_document(chat_id=message.chat.id, document=f, caption=f"📋 Консультация #{request.id}")

        logger_admin.info(f"Админ посмотрел консультацию с id {app_id}, файл подготовлен: {filename}")
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

        logger_admin.info(f"Админ посмотрел список консультаций")
        await bot.send_message(chat_id=message.chat.id, text=text)

@bot.message_handler(commands=['req'])
async def view_problem_appointment(message):
    user_id = message.from_user.id
    username = message.from_user.username
    user = await MaxService.get_user(user_id)

    if not AdminService.is_admin(user_id):
        logger_admin.warning(f"Пользователь {user_id} не является админом")
        await bot.send_message(chat_id=message.chat.id, text="⛔ Нет доступа")
        return

    parts = message.text.split()

    if len(parts) >= 2:
        try:
            app_id = int(parts[1])
        except ValueError:
            logger_admin.warning(f"Админ {user_id} ввел неверный формат для просмотра информации по обращению")
            await bot.send_message(chat_id=message.chat.id,
                                   text="❌ Неверный формат. Используйте: /con <id>(порядковый номер записи)")
            return

        request = await AdminService.get_problem_request_by_id(app_id)
        if not request:
            logger_admin.warning(f"Обращение с id {app_id} не найдена")
            await bot.send_message(chat_id=message.chat.id, text=f"❌ Заявка с ID {app_id} не найдена")
            return

        await MaxService.mark_request_viewed(app_id)

        md_content = f"# 🐞 Обращение в техподдержку\n\n"
        md_content += f"**Пользователь:** {user_id}\n"
        md_content += f"**Username:** {username}\n"
        md_content += f"**Мессенджер:** {user.platform}\n"
        md_content += f"**Время:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
        md_content += "---\n\n"
        md_content += "## 💬 Последние сообщения\n\n"
        md_content += request.messages if request.messages else "Нет сообщений"

        filename = f"bot_report_{user_id}_{int(datetime.now().timestamp())}.txt"
        async with aiofiles.open(filename, "w", encoding='utf-8') as f:
            await f.write(md_content)
        with open(filename, "rb") as f:
            await bot.send_document(chat_id=message.chat.id, document=f, caption=f"📋 Новое обращение от пользователя")

        logger_admin.info(f"Админ {user_id} посмотрел обращение с id {app_id}, файл подготовлен: {filename}")
        os.remove(filename)

    else:
        appointments = await AdminService.get_unviewed_problem_request()

        if not appointments:
            await bot.send_message(chat_id=message.chat.id, text="Нет новых обращений")
            return

        text = "📋 **Обращения в поддержку:**\n\n"
        for apps in appointments:
            status = "✅" if apps.viewed else "🆕"
            text += f"{status} id:{apps.id} — {datetime.now().strftime('%d.%m.%Y 20:00')} — {apps.contact}\n"

        text += "\n📝 Для просмотра деталей: /req <id>(порядковый номер записи)"

        logger_admin.info(f"Админ {user_id} посмотрел список обращений")
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
        "🔹 /req — посмотреть обращения пользователей\n"
        "🔹 /ha — помощь по командам\n\n"
    )

    await bot.send_message(chat_id=message.chat.id, text=text)

# logic
@bot.callback_query_handler(func=lambda call: call.data == "delete_agree")
async def handle_delete_info_agree(call: CallbackQuery):
    user_id = call.from_user.id

    await MaxService.delete_session(user_id)
    await MaxService.create_session(user_id)
    logger.info("Пользователь успешно удалил все свои данные")

    # noinspection PyUnresolvedReferences
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Все данные удалены. Начинай снова /new"
    )

@bot.callback_query_handler(func=lambda call: call.data == "delete_disagree")
async def handle_delete_info_disagree(call: CallbackQuery):
    user_id = call.from_user.id
    logger.info(f"Пользователь {user_id} отменил удаление данных")

    # noinspection PyUnresolvedReferences
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

    # noinspection PyUnresolvedReferences
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
    # noinspection PyUnresolvedReferences
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

    # noinspection PyUnresolvedReferences
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Отлично. Что хочешь дальше?\n\nВыбирай❗",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data == "query")
async def handle_query(call: CallbackQuery):
    user_id = call.from_user.id
    logger.info(f"Пользователь {user_id} делает выбор памяти")
    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(text="Без памяти", callback_data="memory_none"),
        InlineKeyboardButton(text="Один диалог", callback_data="memory_dialog"),
        InlineKeyboardButton(text="Вся память", callback_data="memory_full")
    )

    # noinspection PyUnresolvedReferences
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
    payment_data = TochkaApiService().create_payment_link(14)

    if not payment_data or not payment_data.get("payment_link"):
        # noinspection PyUnresolvedReferences
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

    # noinspection PyUnresolvedReferences
    await bot.send_message(
        chat_id=call.message.chat.id,
        text=(
            "Ты посмотрел видео и выбрал память. Оцени свой уровень доверия ⚠️ Если информации недостаточно, изучи сайт👇 Сначала тест, потом автоматические списания по 650р каждый месяц ❗️ Если что-то не понял и хочешь вернуться назад, напиши /new"
        ),
        reply_markup=kb
    )
    await asyncio.sleep(2)
    # noinspection PyUnresolvedReferences
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
    logger.info(f"Тип памяти {MemoryMode.none} выбран для пользователя {user_id}")

    user = await MaxService.get_user(user_id)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="видео", url="https://disk.yandex.ru/i/F8LpWWDviR-Erw"))

    # noinspection PyUnresolvedReferences
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
    logger.info(f"Тип памяти {MemoryMode.none} изменен для пользователя {user_id}")

    # noinspection PyUnresolvedReferences
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text='Выбор памяти изменен на "Без памяти"\n\nМожете продолжить диалог.'
    )

@bot.callback_query_handler(func=lambda call: call.data == "memory_dialog")
async def handle_memory_dialog(call: CallbackQuery):
    user_id = call.from_user.id
    await MaxService.update_memory_mode(user_id, MemoryMode.session)
    logger.info(f"Тип памяти {MemoryMode.session} выбран для пользователя {user_id}")

    user = await MaxService.get_user(user_id)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="видео", url="https://disk.yandex.ru/i/F8LpWWDviR-Erw"))

    # noinspection PyUnresolvedReferences
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
    logger.info(f"Тип памяти {MemoryMode.session} изменен для пользователя {user_id}")

    # noinspection PyUnresolvedReferences
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
    logger.info(f"Тип памяти {MemoryMode.full} выбран для пользователя {user_id}")

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="видео", url="https://disk.yandex.ru/i/F8LpWWDviR-Erw"))

    # noinspection PyUnresolvedReferences
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
    logger.info(f"Тип памяти {MemoryMode.full} измене для пользователя {user_id}")

    # noinspection PyUnresolvedReferences
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text='Выбор памяти изменен на "Вся память"\n\nМожете продолжить диалог.'
    )

@bot.callback_query_handler(func=lambda call: call.data == "consult_agree")
async def handle_consult_agree(call: CallbackQuery):
    user_id = call.from_user.id

    # noinspection PyUnresolvedReferences
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    logger.info(f"Пользователь {user_id} продолжил запись на консультацию")

    contact_button = KeyboardButton(
        text="📱 Поделиться номером",
        request_contact=True
    )

    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )
    keyboard.add(contact_button)

    # noinspection PyUnresolvedReferences
    await bot.send_message(
        chat_id=call.message.chat.id,
        text="Пожалуйста, поделись своим номером телефона, чтобы я мог записать тебя на консультацию.",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "consult_disagree")
async def handle_consult_disagree(call: CallbackQuery):
    user_id = call.from_user.id
    logger.info(f"Пользователь {user_id} отменил запись на консультацию")

    # noinspection PyUnresolvedReferences
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Ты отменил заявку на консультацию. Если хочешь записаться на консультацию - /igor"
    )

@bot.callback_query_handler(func=lambda call: call.data == "cancel_subscription")
async def cancel_subscription_callback(call: CallbackQuery):
    user_id = call.from_user.id

    user = await MaxService.get_user(user_id)

    if user.subscription_status not in (SubsStatus.active, SubsStatus.grace_period):
        logger.warning(f"Пользователь {user_id} не имеет активной подписки")
        # noinspection PyUnresolvedReferences
        await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="❌ У вас нет активной подписки для отмены."
    )
        return

    await MaxService.change_subscription_status(user_id, SubsStatus.cancelled)
    logger.info(f"Пользователь {user_id} успешно отменил подписку, статус подписки: {SubsStatus.cancelled}")

    # noinspection PyUnresolvedReferences
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ Подписка отменена.\n"
             f"Доступ сохранится до {user.subscription_ends_at.strftime('%d.%m.%Y')}.\n"
             f"Чтобы возобновить, оплатите через /sub"
    )

@bot.callback_query_handler(func=lambda call: call.data == "bot_send_problem")
async def bot_report(call: CallbackQuery):
    user_id = call.from_user.id

    history = await MaxService.get_last_messages(user_id, limit=20)

    history_text = "\n".join([
        f"{'🧑 Клиент' if msg.role == 'user' else '🤖 Бот'}: {msg.content}"
        for msg in history
    ])

    await AdminService.add_problem_request(
        client_id=user_id,
        messages=history_text
    )

    logger.info(f"Пользователь {user_id} отправил обращение")
    # noinspection PyUnresolvedReferences
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="✅ Обращение отправлено! Богдан разберётся в ближайшее время 😉"
    )

@bot.callback_query_handler(func=lambda call: call.data == "bot_dsend")
async def bot_cancel(call: CallbackQuery):
    user_id = call.from_user.id
    logger.info(f"Пользователь {user_id} остановил отправку обращения")

    # noinspection PyUnresolvedReferences
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="❌ Обращение отменено. Если передумаешь — напиши /bot"
    )

# message
@bot.message_handler(content_types=['contact'])
async def handle_contact(message):
    contact = message.contact
    user_id = message.from_user.id

    phone = contact.phone_number

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
    logger.info(f"Пользователь {user_id} успешно поделился своим контактом")

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

    logger.info(f"Пользователь {user_id} отправил голосовое сообщение")

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        await bot.send_message(
            chat_id=message.chat.id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    elif not await MaxService.can_send_message(user_id):
        logger.warning(f"У пользователя {user_id} не активирована подписка - нет возможности писать")
        await bot.send_message(
            chat_id=message.chat.id,
            text="🔒 Ваша подписка не активна.\nПожалуйста, оплатите доступ в /sub"
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
                    await MaxService.add_message(user_id, session_user.id, "user", recognized_text)
                    await MaxService.add_message(user_id, session_user.id, "assistant", answer)
                await bot.send_message(chat_id=message.chat.id, text=answer)
                logger.info(f"Пользователь {user_id} успешно получил ответ от ассистента")
            else:
                logger.error(f"Пользователь {user_id} не получил ответ")
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="⚠️ Не удалось получить ответ. Попробуйте позже."
                )
        except Exception as e:
            logger.exception(f"Ошибка обработки голосового сообщения от пользователя {user_id}, ошибка: {e}")
            await bot.send_message(chat_id=message.chat.id, text="⚠️ Ошибка обработки голосового. Попробуйте текстом.")

@bot.message_handler(func=lambda message: True)
async def handle_message(message):
    text = message.text
    if text.startswith('/'):
        return

    user_id = message.from_user.id
    user_reg = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    logger.info(f"Пользователь {user_id} отправил сообщение: {text[:10]}")

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        await bot.send_message(
            chat_id=message.chat.id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    elif not await MaxService.can_send_message(user_id):
        logger.warning(f"У пользователя {user_id} не активирована подписка - нет возможности писать")
        await bot.send_message(
            chat_id=message.chat.id,
            text="🔒 Ваша подписка не активна.\nПожалуйста, оплатите доступ в /sub"
        )
        return

    else:
        selected_topic = "Консультации"
        index_id = THEMES_INDEXES.get(selected_topic)
        history = await MaxService.get_history(user_id, limit=200)
        answer = ask_ai_with_index(index_id, text, selected_topic, history)

        if answer:
            if user_reg.memory_mode != MemoryMode.none:
                await MaxService.add_message(user_id, session_user.id, "user", text)
                await MaxService.add_message(user_id, session_user.id, "assistant", answer)
            await bot.send_message(chat_id=message.chat.id, text=answer)
            logger.info(f"Пользователь {user_id} успешно получил ответ от ассистента")
        else:
            logger.error(f"Пользователь {user_id} не получил ответ")
            await bot.send_message(
                chat_id=message.chat.id,
                text="⚠️ Не удалось получить ответ. Попробуйте позже."
            )

# started
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
    logger.info("Бот успешно запущен")
    await asyncio.Event().wait()

# started
if __name__ == "__main__":
    asyncio.run(main())

