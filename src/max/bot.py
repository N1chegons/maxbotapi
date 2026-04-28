import asyncio
import logging
import aiohttp

from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import Command
from maxapi.types import MessageCreated, BotStarted, CallbackButton, MessageCallback
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

# from src.admin.repository import AdminService
from src.config import settings
from src.max.repository import MaxService, AudioService
from src.max.utils import upload_to_s3
from src.yandexai.config import THEMES_INDEXES
from src.yandexai.orchestrator import ask_ai_with_index

logging.basicConfig(level=logging.INFO)
TOKEN = settings.MAX_BOT_TOKEN

bot = Bot(TOKEN)
dp = Dispatcher()

# Command
@dp.message_created(Command('new'))
async def new_theme(event: MessageCreated):
    user_id = event.from_user.user_id

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
            "Привет 👋\n"
            "Я — Бот психолога Игоря Неповинных.\n\n"
            "Не «ещё один GPT», а цифровой Игорь, обученный на 15 годах практики, двух его книгах и 800+ видео.\n\n"
            "❗ Прежде чем начнём — пара важных вещей.\n"
            "Займёт минуту."
        ),
        attachments=[reply_kb.as_markup()]
    )

#
# @dp.message_created(Command('igor'))
# async def igor_command(event: MessageCreated,  context: MemoryContext):
#     user_id = event.from_user.user_id
#     username = event.from_user.username
#
#     await AdminService.log_command_admin(user_id, "/igor")
#
#     already_request = await MaxService.get_request(user_id)
#     if already_request:
#         await bot.send_message(
#             user_id=user_id,
#             text="✔️ Вы уже отправили заявку на консультацию!\n\nВы можете продолжить задавать вопросы."
#         )
#
#     else:
#         reply_kb = InlineKeyboardBuilder()
#         reply_kb.row(
#             MessageButton(text="✅ ДА"),
#             MessageButton(text="❌ НЕТ"),
#         )
#
#         await context.set_state(ConsultChoice.ant_choice)
#
#         await bot.send_message(
#         user_id=user_id,
#         text=(
#             "Подумай ещё раз...\n"
#             "Игорь берёт не всех и не каждого.\n"
#             "Я сохраню последние двадцать сообщений: передам их Игорю.\n"
#             "Он оценит качество гипотезы и напишет тебе.\n\n"
#             "Ты уверен?(Выбери ДА/НЕТ)"
#         ),
#         attachments=[reply_kb.as_markup()]
#     )
#
# @dp.message_created(Command('mark'))
# async def mark_command(event: MessageCreated, context: MemoryContext):
#     user_id = event.from_user.user_id
#     await AdminService.log_command_admin(user_id, "/new")
#
#     data = await context.get_data()
#     last_exchange = data.get("last_exchange")
#     last_topic = data.get("last_topic")
#
#     if not last_exchange:
#         await bot.send_message(
#             user_id=user_id,
#             text="⚠️ Нет сообщений для отметки. Сначала задайте вопрос."
#         )
#         return
#
#     await MaxService.add_feedback(
#         client_id=user_id,
#         fragment=last_exchange,
#         is_positive=True,
#         session_topic=last_topic
#     )
#
#     await bot.send_message(
#         user_id=user_id,
#         text="✔️ Спасибо за похвалу. Эксперт увидит что вы меня похвалили.\n"
#              "Можете продолжить диалог."
#     )
#
# @dp.message_created(Command('hren'))
# async def hren_command(event: MessageCreated, context: MemoryContext):
#     user_id = event.from_user.user_id
#     await AdminService.log_command_admin(user_id, "/hren")
#
#     data = await context.get_data()
#     last_exchange = data.get("last_exchange")
#     last_topic = data.get("last_topic")
#
#     if not last_exchange:
#         await bot.send_message(
#             user_id=user_id,
#             text="⚠️ Нет сообщений для отметки. Сначала задайте вопрос."
#         )
#         return
#
#     await MaxService.add_feedback(
#         client_id=user_id,
#         fragment=last_exchange,
#         is_positive=False,
#         session_topic=last_topic
#     )
#
#     await bot.send_message(
#         user_id=user_id,
#         text="✔️ Думаю что сделал что-то не так. Эксперт увидит что вы меня поругали.\n"
#              "Можете продолжить диалог."
#     )
#
# @dp.message_created(Command('help'))
# async def help_command(event: MessageCreated):
#     user_id = event.from_user.user_id
#
#     help_text = (
#             "📋 **Доступные команды**\n\n"
#             "🔹 /new — сменить тему консультации (Путь, Консультации, Теория, Мировоззрение)\n"
#             "🔹 /mark — похвалить бота (попадёт в отчёт эксперту)\n"
#             "🔹 /hren - поругать бота (попадёт в отчёт эксперту)\n"
#             "🔹 /igor — записаться на личную консультацию к эксперту\n"
#             "🔹 /help — показать список команд\n\n"
#             "💡 **Как пользоваться:**\n"
#             "• Просто пишите свои вопросы — я помогу разобраться\n"
#             "• Я задаю уточняющие вопросы и предлагаю гипотезы\n"
#             "• Всё, что мы обсуждаем, конфиденциально\n\n"
#             "✨ Готовы продолжить? Напишите, что вас беспокоит."
#         )
#
#     await bot.send_message(
#         user_id=user_id,
#         text=help_text
#     )


# admin-panel


# @dp.message_created(Command('admin'))
# async def admin_panel(event: MessageCreated):
#     user_id = event.from_user.user_id
#     if not AdminService.is_admin(user_id):
#         await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
#         return
#
#     text = (
#         "👋 **Добро пожаловать в админ-панель!**\n\n"
#         "📊 **Доступные команды:**\n\n"
#         "🔹 /st [дни] - просмотр статистки за кол-во дней(по умолчанию 1)\n"
#         "🔹 /mh — последние 5 отметок /mark\n"
#         "🔹 /hh — последние 5 отметок /hren\n"
#         "🔹 /con — посмотреть заявки на консультацию\n"
#         "🔹 /ha — помощь по командам\n\n"
#     )
#
#     await bot.send_message(user_id=user_id, text=text)
#
# @dp.message_created(Command('st'))
# async def stats_command(event: MessageCreated):
#     user_id = event.from_user.user_id
#     if not AdminService.is_admin(user_id):
#         await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
#         return
#
#     parts = event.message.body.text.split()
#     days = 1
#
#     if len(parts) > 1:
#         try:
#             days = int(parts[1])
#             if days < 1:
#                 days = 1
#             if days > 365:
#                 days = 365
#         except ValueError:
#             await bot.send_message(user_id=user_id, text="❌ Неверный формат. Используйте: `/stats [дни]`")
#             return
#
#     stats = await AdminService.get_commands_stats_admin(days)
#     count_message = await AdminService.get_total_messages_last_days_admin()
#     total_commands =  sum(stats.values())
#
#     report = f"📊 **Всего сообщений за {days} дн.: {count_message}**\n"
#     report += f"⚙️ **Всего команд использовано: {total_commands}**\n\n"
#     report += f"/mark: {stats.get('/mark', 0)}\n"
#     report += f"/hren: {stats.get('/hren', 0)}\n"
#     report += f"/igor: {stats.get('/igor', 0)}\n"
#
#     await bot.send_message(user_id=user_id, text=report)
#
# @dp.message_created(Command('mh'))
# async def stats_command(event: MessageCreated):
#     user_id = event.from_user.user_id
#     if not AdminService.is_admin(user_id):
#         await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
#         return
#
#     marks = await AdminService.get_last_feedbacks_admin(True)
#
#     if not marks:
#         await bot.send_message(user_id=user_id, text="Нет отметок /mark")
#         return
#
#     report = "📊 **Последние 5 сообщений /mark**\n\n"
#     for m in marks:
#         report += f"📅 Дата: {m.created_at.strftime('%d.%m.%Y %H:%M')}\n"
#         report += f"📝 Фрагмент: {m.fragment}...\n\n"
#
#     await bot.send_message(user_id=user_id, text=report)
#
# @dp.message_created(Command('hh'))
# async def stats_command(event: MessageCreated):
#     user_id = event.from_user.user_id
#     if not AdminService.is_admin(user_id):
#         await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
#         return
#
#     hrens = await AdminService.get_last_feedbacks_admin(False)
#
#     if not hrens:
#         await bot.send_message(user_id=user_id, text="Нет отметок /hren")
#         return
#
#     report = "📊 **Последние 5 сообщений /hren**\n\n"
#     for h in hrens:
#         report += f"📅 Дата: {h.created_at.strftime('%d.%m.%Y %H:%M')}\n"
#         report += f"📝 Фрагмент: {h.fragment}...\n\n"
#
#     await bot.send_message(user_id=user_id, text=report)
#
# @dp.message_created(Command('con'))
# async def view_appointment(event: MessageCreated):
#     user_id = event.from_user.user_id
#     if not AdminService.is_admin(user_id):
#         await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
#         return
#
#     parts = event.message.body.text.split()
#
#     if len(parts) >= 2:
#         try:
#             app_id = int(parts[1])
#         except ValueError:
#             await bot.send_message(user_id=user_id, text="❌ Неверный формат. Используйте: /con <id>(порядковый номер записи)")
#             return
#
#         request = await MaxService.get_request_by_id(app_id)
#         if not request:
#             await bot.send_message(user_id=user_id, text=f"❌ Заявка с ID {app_id} не найдена")
#             return
#
#         await MaxService.mark_request_viewed(app_id)
#
#         md_content = f"# 📋 Консультация #{request.id}\n\n"
#         md_content += f"Клиент: {request.client_id}\n"
#         md_content += f"Контакт: {request.contact}\n"
#         md_content += f"Запись на: {request.appointment_date.strftime('%d.%m.%Y %H:%M')}\n"
#         md_content += f"Дата подачи заявки: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
#         md_content += "---\n\n"
#         md_content += "## 💬 Последние сообщения\n\n"
#         md_content += request.messages if request.messages else "Нет сохранённых сообщений"
#
#         filename = f"consultation_{request.client_id}.md"
#         async with aiofiles.open(filename, "w", encoding='utf-8') as f:
#             await f.write(md_content)
#
#         await bot.send_message(
#             user_id=user_id,
#             text=f"📋 Консультация #{request.id}",
#             attachments=[
#                 InputMedia(
#                     path=filename,
#                 )
#             ]
#         )
#
#         await os.remove(filename)
#
#     else:
#         appointments = await MaxService.get_unviewed_request()
#
#         if not appointments:
#             await bot.send_message(user_id=user_id, text="Нет новых заявок на консультацию")
#             return
#
#         text = "📋 **Новые заявки на консультацию:**\n\n"
#         for app in appointments:
#             text += f"{app.id} — {app.appointment_date.strftime('%d.%m.%Y 20:00')} — клиент {app.contact}\n"
#
#         text += "\n📝 Для просмотра деталей: /con <id>(порядковый номер записи)"
#
#         await bot.send_message(user_id=user_id, text=text)
#
# @dp.message_created(Command('ha'))
# async def admin_help_command(event: MessageCreated):
#     user_id = event.from_user.user_id
#
#     if not AdminService.is_admin(user_id):
#         await bot.send_message(user_id=user_id, text="⛔ Нет доступа")
#         return
#
#     text = (
#         "📊 **Доступные команды:**\n\n"
#         "🔹 /st [дни] - просмотр статистки за кол-во дней(по умолчанию 1)\n"
#         "🔹 /mh — последние 5 отметок /mark\n"
#         "🔹 /hh — последние 5 отметок /hren\n"
#         "🔹 /con — посмотреть заявки на консультацию\n"
#         "🔹 /ha — показать это сообщение"
#     )
#
#     await bot.send_message(user_id=user_id, text=text)

# logic
@dp.bot_started()
async def bot_started(event: BotStarted):
    user_id = event.user.user_id

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
           "Привет 👋\n"
           "Я — Бот психолога Игоря Неповинных.\n\n"
           "Не «ещё один GPT», а цифровой Игорь, обученный на 15 годах практики, двух его книгах и 800+ видео.\n\n"
           "❗ Прежде чем начнём — пара важных вещей.\n"
           "Займёт минуту."
        ),
        attachments=[reply_kb.as_markup()]
    )

@dp.message_callback(F.callback.payload == "continue")
async def handle_continue(callback: MessageCallback):
    user_id = callback.message.sender.user_id
    # user = repo.get(user_id)
    #
    # # Меняем состояние
    # user.state = UserState.ONBOARDING_DISCLAIMER
    # repo.save(user)

    # Показываем дисклеймер

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
            "Кризисные ситуации (суицид, насилие в семье, острая боль) - не ко мне.\n\n"
            "Я успокою голову и сделаю тебя сильным. Согласен?\nТогда давай знакомиться."
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
    reply_kb = InlineKeyboardBuilder()
    reply_kb.row(
        CallbackButton(
            text="Запрос >",
            payload="query"
        ),
        CallbackButton(
            text="про Бота >",
            payload="aboutbot"
        ),
        CallbackButton(
            text="про Эксперта >",
            payload="aboutexpert"
        ),
    )

    await callback.message.edit(
        text=(
            "Отлично. Что хочешь дальше?\n Выбирай."
        ),
        attachments = [reply_kb.as_markup()]
    )

@dp.message_callback(F.callback.payload == "query")
async def handle_query(callback: MessageCallback):
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

@dp.message_callback(F.callback.payload == "aboutbot")
async def handle_info_work(message: MessageCreated):
    user_id = message.from_user.user_id

    await bot.send_message(
        text=(
            "Заглушка"
        )
    )

@dp.message_callback(F.callback.payload == "aboutexpert")
async def handle_who_igor(callback: MessageCallback):

    await callback.message.edit(
        text=(
            "Заглушка"
        )
    )


@dp.message_callback(F.callback.payload == "memory_none")
async def handle_memory_none(callback: MessageCallback):
    await callback.message.edit(
        text="Напиши, что тебя беспокоит прямо сейчас.\n Для начала нам нужна та эмоция, которая актуальна в данный момент. Что ты чувствуешь? Что переживаешь?",
        attachments=[]
    )

@dp.message_callback(F.callback.payload == "memory_dialog")
async def handle_memory_dialog(callback: MessageCallback):
    # user = repo.get(user_id)
    #
    # # Сохраняем выбранный режим памяти
    # choice = message.text
    # if choice == "/memory_none":
    #     user.memory_mode = "none"
    # elif choice == "/memory_session":
    #     user.memory_mode = "session"
    # elif choice == "/memory_full":
    #     user.memory_mode = "full"
    #
    # # Меняем состояние
    # user.state = UserState.ONBOARDING_MENU
    # repo.save(user)

    # Показываем главное меню
    await callback.message.edit(
        text="Напиши, что тебя беспокоит прямо сейчас.\n Для начала нам нужна та эмоция, которая актуальна в данный момент. Что ты чувствуешь? Что переживаешь?", attachments=[]
    )

@dp.message_callback(F.callback.payload == "memory_full")
async def handle_memory_full(callback: MessageCallback):
    # user = repo.get(user_id)
    #
    # # Сохраняем выбранный режим памяти
    # choice = message.text
    # if choice == "/memory_none":
    #     user.memory_mode = "none"
    # elif choice == "/memory_session":
    #     user.memory_mode = "session"
    # elif choice == "/memory_full":
    #     user.memory_mode = "full"
    #
    # # Меняем состояние
    # user.state = UserState.ONBOARDING_MENU
    # repo.save(user)

    # Показываем главное меню
    await callback.message.edit(
        text="Напиши, что тебя беспокоит прямо сейчас.\n Для начала нам нужна та эмоция, которая актуальна в данный момент. Что ты чувствуешь? Что переживаешь?", attachments=[]
    )

# --Consult
# @dp.message_created(ConsultChoice.ant_choice)
# async def igor_confirm(event: MessageCreated, context: MemoryContext):
#     user_id = event.from_user.user_id
#     answer = event.message.body.text.strip()
#
#     if answer in ["✅ ДА", "ДА", "YES", "Да", "да"]:
#         await bot.send_message(
#             user_id=user_id,
#             text="📞 **Поделитесь контактом** — напишите номер вручную: +7XXXXXXXXXX"
#         )
#
#         await context.set_state(WaitingForPhone.waiting)
#
#     elif answer in ["❌ НЕТ", "НЕТ", "NO", "Нет", "нет"]:
#         await bot.send_message(
#             user_id=user_id,
#             text="❌ Вы отменили заявку на консультацию.\n\nЕсли передумаешь — напиши `/igor` снова."
#         )
#         await context.set_state(None)
#     else:
#         await bot.send_message(
#             user_id=user_id,
#             text="Пожалуйста, ответь ДА или НЕТ."
#         )
#         return
#
# @dp.message_created(WaitingForPhone.waiting)
# async def phone_added(event: MessageCreated, context: MemoryContext):
#     user_id = event.from_user.user_id
#     text = event.message.body.text.strip()
#
#     phone_number = None
#     if text.replace('+', '').replace(' ', '').isdigit():
#         phone_number = text
#
#     if not phone_number:
#         await bot.send_message(
#             user_id=user_id,
#             text="❓ Пожалуйста, отправьте номер телефона цифрами (например, +79161234567)."
#         )
#         return
#
#     history = await MaxService.get_last_messages(user_id, limit=20)
#     history_text = "\n".join([
#         f"{'🧑 Клиент' if msg.role == 'user' else '🤖 Бот'}: {msg.content}"
#         for msg in history
#     ])
#
#     appointment_date = await MaxService.get_next_free_date()
#
#     await MaxService.add_request(
#         client_id=user_id,
#         contact=phone_number,
#         messages=history_text,
#         appointment_date=appointment_date
#     )
#
#     await context.set_state(None)
#     await bot.send_message(
#         user_id=user_id,
#         text="✅ Спасибо! Игорь свяжется с вами для подтверждения консультации.\n\n"
#              "Вы можете продолжить вести диалог."
#     )
#
@dp.message_created(F.message.body.text)
async def handle_message(event: MessageCreated):
    user_id = event.from_user.user_id
    text = event.message.body.text
    if text.startswith('/'):
        return

    session = await MaxService.get_session(user_id)
    selected_topic = "Консультации"
    index_id = THEMES_INDEXES.get(selected_topic)

    if not index_id:
        await bot.send_message(
            user_id=user_id,
            text="⚠️ Ошибка: индекс для этой темы не найден"
        )
        return

    history = await MaxService.get_history(user_id, limit=10)
    await MaxService.add_message(user_id, "user", text)

    answer = ask_ai_with_index(index_id, text, selected_topic, history)

    if answer:
        last_exchange = f"Клиент: {text}\n\nБот: {answer}"

        await MaxService.add_message(user_id, "assistant", answer)
        await bot.send_message(user_id=user_id, text=answer)
    else:
        await bot.send_message(
            user_id=user_id,
            text="⚠️ Не удалось получить ответ. Попробуйте позже."
        )

@dp.message_created(F.message.body.attachments)
async def handle_voice_message(event: MessageCreated):
    user_id = event.from_user.user_id

    session = await MaxService.get_session(user_id)
    selected_topic = "Консультации"
    index_id = THEMES_INDEXES.get(selected_topic)

    history = await MaxService.get_history(user_id, limit=10)

    if not index_id:
        await bot.send_message(
            user_id=user_id,
            text="⚠️ Ошибка: индекс для этой темы не найден"
        )
        return


    audio_attachment = None
    for att in event.message.body.attachments:
        if att.type == "audio":
            audio_attachment = att
            break
    if not audio_attachment:
        return
    audio_url = audio_attachment.payload.url

    try:
        headers = {"User-Agent": "MAX/1.0", "Referer": "https://max.ru/"}
        async with aiohttp.ClientSession() as session_audio:
            async with session_audio.get(audio_url, headers=headers) as resp:
                audio_data = await resp.read()

        s3_url = await upload_to_s3(audio_data)

        recognized_text = AudioService.recognize_from_s3(s3_url, settings.YC_API_KEY)

        answer = ask_ai_with_index(index_id, recognized_text, selected_topic, history)
        if answer:
            last_exchange = f"Клиент: {recognized_text}\n\nБот: {answer}"
            await MaxService.add_message(user_id, "user", recognized_text)
            await MaxService.add_message(user_id, "assistant", answer)
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
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())