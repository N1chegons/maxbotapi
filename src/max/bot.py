import asyncio
import os
from datetime import datetime
from typing import Any

import aiofiles
import aiohttp
import magic
import subprocess

from src.logger_config import setup_logger
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

logger = setup_logger('max_bot', 'max', 'MAX_bot.log')
logger_admin = setup_logger('admin', 'admin','max_admin.log')

TOKEN = settings.MAX_BOT_TOKEN

bot = Bot(TOKEN)
dp = Dispatcher()

from src.max.repository import MaxService, AudioService

# Command
@dp.message_created(Command('new'))
async def new_session(event: MessageCreated):
    # noinspection PyUnresolvedReferences
    user_id = event.message.sender.user_id
    logger.debug(f"Обновление сессии для пользователя {user_id}")
    await MaxService.delete_session(user_id)
    await MaxService.create_session(user_id)
    await MaxService.update_user_state(user_id, UserState.NEW)
    logger.info(f"Сессия для пользователя {user_id} обновлена")

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
    # noinspection PyUnresolvedReferences
    user_id = event.message.sender.user_id
    session_user = await MaxService.get_session(user_id)
    logger.info(f"Смена памяти для пользователя {user_id}")

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
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

        reply_kb_vid = InlineKeyboardBuilder()
        reply_kb_vid.row(
            LinkButton(
                text="про Память >",
                url="https://disk.yandex.ru/i/4N1TT70-vEuRwg"
            )
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

        await bot.send_message(
            user_id=user_id,
            text="Можешь посмотреть видео",
            attachments=[reply_kb_vid.as_markup()]
        )

@dp.message_created(Command('del'))
async def delete_info(event: MessageCreated):
    # noinspection PyUnresolvedReferences
    user_id = event.message.sender.user_id
    session_user = await MaxService.get_session(user_id)
    logger.info(f"Удаление данных для пользователя {user_id}")

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
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


# noinspection PyUnresolvedReferences
@dp.message_created(Command('end'))
async def closed_session(event: MessageCreated):
    user_id = event.message.sender.user_id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)
    logger.info(f"Пользователь {user_id} заканчивает диалог")

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        await bot.send_message(
            user_id=user_id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )
    else:
        history = await MaxService.get_history(user_id)
        logger.info(f"Получена история сообщений для пользоватля {user_id}")

        selected_topic = "Консультации"
        index_id = THEMES_INDEXES.get(selected_topic)
        text = f"""
            ПРОМТ для команды /end
                Проанализируй сообщения пользователя и коротко перечисли темы, которые обсудили, плюс выводы, к которым пришли.
            
            Вот все сообщения пользоватля:
            {history}
            """

        answer = ask_ai_with_index(index_id, text, selected_topic, history)

        if user.memory_mode == MemoryMode.session:
            logger.info(f"Пользователь {user_id} заканчивает диалог с памятью {MemoryMode.session}")
            await MaxService.delete_messages(user.user_id)
            await bot.send_message(
                user_id=user_id,
                text=answer
            )
        elif user.memory_mode == MemoryMode.full:
            logger.info(f"Пользователь {user_id} заканчивает диалог с памятью {MemoryMode.full}")
            await bot.send_message(
            user_id=user_id,
                text=answer
            )
        else:
            logger.info(f"Пользователь {user_id} заканчивает диалог с памятью {MemoryMode.none}")
            await bot.send_message(
            user_id=user_id,
                text="Данные не найдены.\nИзмените тип памяти при помощи /mem"
            )


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
@dp.message_created(Command('igor'))
async def igor_command(event: MessageCreated):
    user_id = event.message.sender.user_id
    session_user = await MaxService.get_session(user_id)
    logger.info(f"Запись на консультацию для пользователя {user_id}")

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        await bot.send_message(
            user_id=user_id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    already_request = await MaxService.get_request(user_id)
    if already_request:
        logger.info(f"Пользователь {user_id} уже записан на консультацию")
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


# noinspection PyUnresolvedReferences
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

async def create_payment_link(amount: float, user_id: int) -> Any | None:
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
async def send_sub_buttons(user_id: int, user):
    kb = InlineKeyboardBuilder()

    if user.subscription_status in (SubsStatus.active, SubsStatus.grace_period):
        # noinspection PyDeprecation
        if user.subscription_ends_at and user.subscription_ends_at > datetime.utcnow():
            kb.row(CallbackButton(text="❌ Отменить подписку", payload="cancel_subscription"))
            await bot.send_message(user_id=user_id, text="🔧 Управление подпиской:", attachments=[kb.as_markup()])
            return

    if user.has_started_subscription:
        payment_link = await create_payment_link(650.00, user_id)
        kb.row(LinkButton(text="💳 Оплатить 650 ₽", url=payment_link))
    else:
        # Создаём ссылку на 14 ₽
        payment_link = await create_payment_link(14.00, user_id)
        kb.row(LinkButton(text="💳 14 рублей за 14 дней теста", url=payment_link))

    await bot.send_message(    user_id=user_id, text="Оплатите подписку:", attachments=[kb.as_markup()])
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

    elif user.subscription_status == SubsStatus.cancelled:
        if user.subscription_ends_at and user.subscription_ends_at > now:
            next_date = user.subscription_ends_at
            status_text = "⏸ Отменена (доступ до даты)"
        else:
            status_text = "❌ Истекла"

    else:
        status_text = "❌ Нет активной подписки"

    return status_text, next_date


# noinspection PyUnresolvedReferences
@dp.message_created(Command('sub'))
async def cmd_sub(event: MessageCreated):
    user_id = event.from_user.user_id
    user = await MaxService.get_user(user_id)
    logger.info(f"Проверка подписки для пользователя {user_id}")

    if not user:
        logger.warning(f"Пользователь по {user_id} не найден")
        await bot.send_message(user_id=user_id, text="❌ Пользователь не найден. Напишите /start")
        return

    # Проверяем статус и формируем текст
    status_text, next_date = await get_subscription_status(user)

    text = f"💳 **Подписка**\n"
    text += f"📌 Статус: {status_text}\n"
    text += f"💰 Тариф: Базовый (650 ₽/мес)\n"
    if next_date:
        # noinspection PyDeprecation
        days_left = (next_date - datetime.utcnow()).days
        text += f"📅 Следующее списание: {next_date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Осталось дней: {days_left}\n"

    # Отправляем текст (без кнопок, чтобы не перегружать)
    await bot.send_message(user_id=user_id, text=text)

    # Отправляем кнопки отдельным сообщением
    await send_sub_buttons(user_id, user)

# admin
# noinspection PyUnresolvedReferences
@dp.message_created(Command('admin'))
async def admin_panel(event: MessageCreated):
    user_id = event.message.sender.user_id
    if not AdminService.is_admin(user_id):
        logger_admin.warning(f"Пользователь {user_id} не является админом")
        await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
        return

    text = (
        "👋 **Добро пожаловать в админ-панель!**\n\n"
        "📊 **Доступные команды:**\n\n"
        "🔹 /st [дни] - просмотр статистки за кол-во дней(по умолчанию 1)\n"
        "🔹 /con — посмотреть заявки на консультацию\n"
        "🔹 /req — посмотреть обращения пользователей\n"
        "🔹 /ha — помощь по командам\n\n"
    )

    await bot.send_message(user_id=user_id, text=text)


# noinspection PyUnresolvedReferences
@dp.message_created(Command('st'))
async def stats_command(event: MessageCreated):
    user_id = event.message.sender.user_id
    if not AdminService.is_admin(user_id):
        logger_admin.warning(f"Пользователь {user_id} не является админом")
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

    logger_admin.info(f"Админ {user_id} просмотрел статистику по сообщеиям за {count_message} дней")
    await bot.send_message(user_id=user_id, text=report)


# noinspection PyUnresolvedReferences
@dp.message_created(Command('con'))
async def view_appointment(event: MessageCreated):
    user_id = event.message.sender.user_id
    if not AdminService.is_admin(user_id):
        logger_admin.warning(f"Пользователь {user_id} не является админом")
        await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
        return

    parts = event.message.body.text.split()

    if len(parts) >= 2:
        try:
            app_id = int(parts[1])
        except ValueError:
            logger_admin.warning(f"Админ {user_id} ввел неверный формат для просмотра информации по консультации")
            await bot.send_message(user_id=user_id, text="❌ Неверный формат. Используйте: /con <id>(порядковый номер записи)")
            return

        request = await MaxService.get_request_by_id(app_id)
        if not request:
            logger_admin.warning(f"Консультация с id {app_id} не найдена")
            await bot.send_message(user_id=user_id, text=f"❌ Заявка с ID {app_id} не найдена")
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

        filename = f"consultation_{request.client_id}.md" if request.client_id else f"consultation_{request.created_at.strftime('%d_%m_%Y')}.md"
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

        logger_admin.info(f"Админ посмотрел консультацию с id {app_id}, файл подготовлен: {filename}")
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

        logger_admin.info(f"Админ посмотрел список консультаций")
        await bot.send_message(user_id=user_id, text=text)


# noinspection PyUnresolvedReferences
@dp.message_created(Command('req'))
async def view_problem_appointment(event: MessageCreated):
    user_id = event.message.sender.user_id
    username = event.message.sender.first_name or "Не указан"
    user = await MaxService.get_user(user_id)

    if not AdminService.is_admin(user_id):
        logger_admin.warning(f"Пользователь {user_id} не является админом")
        await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
        return

    parts = event.message.body.text.split()

    if len(parts) >= 2:
        try:
            app_id = int(parts[1])
        except ValueError:
            logger_admin.warning(f"Админ {user_id} ввел неверный формат для просмотра информации по обращению")
            await bot.send_message(user_id=user_id, text="❌ Неверный формат. Используйте: /con <id>(порядковый номер записи)")
            return

        request = await AdminService.get_problem_request_by_id(app_id)
        if not request:
            logger_admin.warning(f"Обращение с id {app_id} не найдена")
            await bot.send_message(user_id=user_id, text=f"❌ Обращение с ID {app_id} не найдена")
            return

        await AdminService.mark_request_viewed(app_id)

        md_content = f"# 🐞 Обращение в техподдержку\n\n"
        md_content += f"**Пользователь:** {user_id}\n"
        md_content += f"**Username:** {username}\n"
        md_content += f"**Мессенджер:** {user.platform}\n"
        md_content += f"**Время:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
        md_content += "---\n\n"
        md_content += "## 💬 Последние сообщения\n\n"
        md_content += request.messages if request.messages else "Нет сообщений"

        filename = f"bot_report_{user_id}_{int(datetime.now().timestamp())}.md"
        async with aiofiles.open(filename, "w", encoding='utf-8') as f:
            await f.write(md_content)

        with open(filename, "rb"):
            await bot.send_message(
                user_id=user_id,
                text=f"📋 Новое обращение от пользователя",
                attachments=[
                    InputMedia(
                        path=filename,
                    )
                ]
            )

        logger_admin.info(f"Админ {user_id} посмотрел обращение с id {app_id}, файл подготовлен: {filename}")
        os.remove(filename)

    else:
        appointments = await AdminService.get_unviewed_problem_request()

        if not appointments:
            await bot.send_message(user_id=user_id, text="Нет новых обращений")
            return

        text = "📋 **Обращения в поддержку:**\n\n"
        for app in appointments:
            status = "✅" if app.viewed else "🆕"
            text += f"{status} id:{app.id} — {datetime.now().strftime('%d.%m.%Y 20:00')}\n"

        text += "\n📝 Для просмотра деталей: /req <id>(порядковый номер записи)"

        logger_admin.info(f"Админ {user_id} посмотрел список обращений")
        await bot.send_message(user_id=user_id, text=text)


# noinspection PyUnresolvedReferences
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
        "🔹 /req — посмотреть обращения пользователей\n"
        "🔹 /ha — помощь по командам\n\n"
    )

    await bot.send_message(user_id=user_id, text=text)


# logic
@dp.bot_started()
async def bot_started(event: BotStarted):
    user_id = event.user.user_id
    user = await MaxService.get_user(user_id)
    logger.info(f"Пользователь {user_id} запустил бота")

    if not user:
        await MaxService.create_user(user_id, "MAX")
        await MaxService.create_session(user_id)
        logger.info(f"Пользователь {user_id} успешно зарегестрировался")

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
        logger.info(f"Пользователь {user_id} уже зарегистрирован")
        await bot.send_message(
            user_id=user_id,
            text="Привет 👋"
                 "Ты уже зарегестрирован.\n\n"
                 "Если хочешь начать все сначала пиши - /new"
        )


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "delete_agree")
async def handle_continue(callback: MessageCallback):
    user_id = callback.callback.user.user_id

    await MaxService.delete_session(user_id)
    await MaxService.create_session(user_id)
    logger.info("Пользователь успешно удалил все свои данные")

    await callback.message.edit(
        text="Все данные удалены. Начинай снова /new",
        attachments=[]
    )


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "delete_disagree")
async def handle_continue(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    logger.info(f"Пользователь {user_id} отменил удаление данных")

    await callback.message.edit(
        text="Давай продолжим. На чём мы остановились",
        attachments=[]
    )


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "continue")
async def handle_continue(callback: MessageCallback):
    user_id = callback.callback.user.user_id
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


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "disagree")
async def handle_disagree(callback: MessageCallback):
    await callback.message.edit(
        text=(
            "Понял. Возвращайся, если передумаешь"
        ), attachments=[]
    )


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "query")
async def handle_query(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    logger.info(f"Пользователь {user_id} делает выбор памяти")
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


# noinspection PyUnresolvedReferences
async def handle_agree_subs(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    payment_data = TochkaApiService().create_payment_link(14)

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


# noinspection PyUnresolvedReferences
async def send_video(callback: MessageCallback):
    video = InputMedia(path="video_cache/04.mp4")
    await callback.message.edit(
        text="",
        attachments=[video]
    )


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "memory_none")
async def handle_memory_none(callback: MessageCallback):
    user_id = callback.callback.user.user_id

    await MaxService.update_memory_mode(user_id, MemoryMode.none)
    logger.info(f"Тип памяти {MemoryMode.none} выбран для пользователя {user_id}")

    user = await MaxService.get_user(user_id)

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


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "mem_memory_none")
async def handle_mem_memory_none(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    await MaxService.update_memory_mode(user_id, MemoryMode.none)
    logger.info(f"Тип памяти {MemoryMode.none} изменен для пользователя {user_id}")

    await callback.message.edit(
        text='Выбор памяти изменен на "Без памяти"\n\nМожете продолжить диалог.',
        attachments=[]
    )


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "memory_dialog")
async def handle_memory_dialog(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    await MaxService.update_memory_mode(user_id, MemoryMode.session)
    logger.info(f"Тип памяти {MemoryMode.session} выбран для пользователя {user_id}")

    user = await MaxService.get_user(user_id)

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


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "mem_memory_dialog")
async def handle_mem_memory_dialog(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    await MaxService.update_memory_mode(user_id, MemoryMode.session)
    logger.info(f"Тип памяти {MemoryMode.session} изменен для пользователя {user_id}")

    await callback.message.edit(
        text='Выбор памяти изменен на "Один диалог"\n\nМожете продолжить диалог.',
        attachments=[]
    )


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "memory_full")
async def handle_memory_full(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    user = await MaxService.get_user(user_id)
    logger.info(f"Тип памяти {MemoryMode.full} выбран для пользователя {user_id}")

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


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "mem_memory_full")
async def handle_mem_memory_full(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    await MaxService.update_memory_mode(user_id, MemoryMode.full)
    logger.info(f"Тип памяти {MemoryMode.full} изменен для пользователя {user_id}")

    await callback.message.edit(
        text='Выбор памяти изменен на "Вся память"\n\nМожете продолжить диалог.',
        attachments=[]
    )


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "consult_agree")
async def handle_consult_agree(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    logger.info(f"Пользователь {user_id} продолжил запись на консультацию")

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


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "consult_disagree")
async def handle_consult_disagree(callback: MessageCallback):
    user_id = callback.callback.user.user_id
    logger.info(f"Пользователь {user_id} отменил запись на консультацию")

    await callback.message.edit(
        text="Ты отменил заявку на консультацию. Если хочешь записаться на консультацию - /igor",
        attachments=[]
    )


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "cancel_subscription")
async def cancel_subscription_callback(callback: MessageCallback):
    user_id = callback.callback.user.user_id

    user = await MaxService.get_user(user_id)

    if user.subscription_status not in (SubsStatus.active, SubsStatus.grace_period):
        logger.warning(f"Пользователь {user_id} не имеет активной подписки")
        await callback.message.edit(text="❌ У вас нет активной подписки для отмены.")
        return

    await MaxService.change_subscription_status(user_id, SubsStatus.cancelled)
    logger.info(f"Пользователь {user_id} успешно отменил подписку, статус подписки: {SubsStatus.cancelled}")

    await callback.message.edit(
        text=f"✅ Подписка отменена.\n"
             f"Доступ сохранится до {user.subscription_ends_at.strftime('%d.%m.%Y')}.\n"
             f"Чтобы возобновить, оплатите через /sub"
    )


# noinspection PyUnresolvedReferences
@dp.message_callback(F.callback.payload == "bot_send_problem")
async def bot_report(callback: MessageCallback):
    user_id = callback.callback.user.user_id
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
        text="❌ Обращение отменено. Если передумаешь — напиши /bot"
    )

# messages
# noinspection PyUnresolvedReferences
@dp.message_created(F.message.body.text)
async def handle_message(event: MessageCreated):
    text = event.message.body.text
    if text.startswith('/'):
        return

    user_id = event.message.sender.user_id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    logger.info(f"Пользователь {user_id} отправил сообщение: {text[10:]}")

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        await bot.send_message(
            user_id=user_id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    elif not await MaxService.can_send_message(user_id):
        logger.warning(f"У пользователя {user_id} не активирована подписка - нет возможности писать")
        await bot.send_message(
            user_id=user_id,
            text="🔒 Ваша подписка не активна.\nПожалуйста, оплатите доступ в /sub"
        )

    else:
        selected_topic = "Консультации"
        index_id = THEMES_INDEXES.get(selected_topic)
        history = await MaxService.get_history(user_id, limit=200)
        # noinspection PyTypeChecker
        answer = ask_ai_with_index(index_id, text, selected_topic, history)

        if answer:
            if user.memory_mode != MemoryMode.none:
                # noinspection PyTypeChecker
                await MaxService.add_message(user_id, session_user.id, "user", text)
                await MaxService.add_message(user_id, session_user.id, "assistant", answer)
            await bot.send_message(user_id=user_id, text=answer)
            logger.info(f"Пользователь успешно получил ответ от ассистента")
        else:
            logger.error(f"Пользователь {user_id} не получил ответ")
            await bot.send_message(
                user_id=user_id,
                text="⚠️ Не удалось получить ответ. Попробуйте позже."
            )


# noinspection PyUnresolvedReferences
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
    logger.info(f"Пользователь {user_id} успешно поделился своим контактом")

    await bot.send_message(
        user_id=event.from_user.user_id,
        text="✅ Спасибо! Игорь свяжется с вами для подтверждения консультации.\n\n"
             "Вы можете продолжить вести диалог.",
    )


# noinspection PyUnresolvedReferences
@dp.message_created(F.message.body.attachments)
async def handle_voice_message(event: MessageCreated):
    user_id = event.message.sender.user_id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    logger.info(f"Пользователь {user_id} отправил голосовое сообщение")

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    if not session_user:
        logger.warning(f"У пользователя {user_id} не найдена сессия")
        await bot.send_message(
            user_id=user_id,
            text="Данные не найдены.\n\nИспользуйте команду /new"
        )

    elif not await MaxService.can_send_message(user_id):
        logger.warning(f"У пользователя {user_id} не активирована подписка - нет возможности писать")
        await bot.send_message(
            user_id=user_id,
            text="🔒 Ваша подписка не активна.\nПожалуйста, оплатите доступ в /sub"
        )

    else:
        selected_topic = "Консультации"
        index_id = THEMES_INDEXES.get(selected_topic)
        history = await MaxService.get_history(user_id, limit=200)


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
                if user.memory_mode != MemoryMode.none:
                    await MaxService.add_message(user_id, session_user.id, "user", recognized_text)
                    await MaxService.add_message(user_id, session_user.id, "assistant", answer)
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

# started
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
    logger.info("Бот успешно запущен")

if __name__ == '__main__':
    asyncio.run(main())

