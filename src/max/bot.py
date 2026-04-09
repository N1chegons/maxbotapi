import asyncio
import logging

from maxapi import Bot, Dispatcher, F
from maxapi.context import MemoryContext
from maxapi.exceptions import MaxApiError
from maxapi.filters.command import Command
from maxapi.types import MessageCreated, BotStarted, MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.config import settings
from src.max.models import ThemeChoice
from src.max.repository import MaxService, AudioService
from src.yandexai.config import THEMES_INDEXES
from src.yandexai.orchestrator import ask_ai_with_index


logging.basicConfig(level=logging.INFO)
TOKEN = settings.MAX_BOT_TOKEN

bot = Bot(TOKEN)
dp = Dispatcher()

# scheduler = AsyncIOScheduler()
#
# scheduler.add_job(
#     send_daily_report,
#     "cron",
#     hour=21,
#     minute=59,
#     id="daily_report"
# )
#
# scheduler.start()


@dp.message_created(Command('change_theme'))
async def change_topic(event: MessageCreated, context: MemoryContext):
    user_id = event.from_user.user_id

    reply_kb = InlineKeyboardBuilder()
    reply_kb.row(
        MessageButton(text="Путь"),
        MessageButton(text="Консультации"),
        MessageButton(text="Теория"),
        MessageButton(text="Мировоззрение")
    )

    await context.set_state(ThemeChoice.first_choice)
    await bot.send_message(
        user_id=user_id,
        text="Выберите новую тему:",
        attachments=[reply_kb.as_markup()]
    )

@dp.message_created(Command('consult'))
async def handle_contact(event: MessageCreated):
    user_id = event.from_user.user_id
    username = event.from_user.username
    already_request = await MaxService.get_request(user_id)
    if already_request:
        await bot.send_message(
            user_id=user_id,
            text="✔️ Вы уже отправили заявку на консультацию!\n\nВы можете продолжить задавать вопросы."
        )
    else:
        await MaxService.add_request(user_id, username)

        await bot.send_message(
            user_id=user_id,
            text="✔️ Заявка отправлена! Скоро с вами свяжутся.\n\nВы можете продолжить задавать вопросы."
        )

@dp.message_created(Command('mark'))
async def mark_command(event: MessageCreated, context: MemoryContext):
    user_id = event.from_user.user_id

    data = await context.get_data()
    last_exchange = data.get("last_exchange")
    last_topic = data.get("last_topic")

    if not last_exchange:
        await bot.send_message(
            user_id=user_id,
            text="⚠️ Нет сообщений для отметки. Сначала задайте вопрос, а затем отправьте /mark"
        )
        return

    await MaxService.add_mark(
        client_id=user_id,
        fragment=last_exchange,
        session_topic=last_topic or "unknown"
    )

    await bot.send_message(
        user_id=user_id,
        text="✔️ Отмечено важное сообщение. Оно попадёт в отчёт эксперту.\n"
             "Можете продолжить диалог."
    )

@dp.message_created(Command('help'))
async def help_command(event: MessageCreated):
    user_id = event.from_user.user_id

    help_text = (
            "📋 **Доступные команды**\n\n"
            "🔹 `/change_theme` — сменить тему (Путь, Консультации, Теория, Мировоззрение)\n"
            "🔹 `/mark` — отметить важное сообщение (попадёт в отчёт эксперту)\n"
            "🔹 `/consult` — записаться на личную консультацию\n"
            "🔹 `/help` — показать список команд\n\n"
            "💡 **Как пользоваться:**\n"
            "• Просто пишите свои вопросы — я помогу разобраться\n"
            "• Я задаю уточняющие вопросы и предлагаю гипотезы\n"
            "• Всё, что мы обсуждаем, конфиденциально\n\n"
            "✨ Готовы продолжить? Напишите, что вас беспокоит."
        )

    await bot.send_message(
        user_id=user_id,
        text=help_text
    )


@dp.bot_started()
async def bot_started(event: BotStarted, context: MemoryContext):
    user_id = event.user.user_id

    already_topic = await MaxService.get_session(user_id)

    if already_topic:
        await bot.send_message(
            user_id=user_id,
            text=(
                f"👋 С возвращением!\n\n"
                f"📚 Вы работаете с темой: **{already_topic.topic}**\n\n"
                "✅ **Что делать дальше?**\n"
                "• Продолжить диалог — просто напишите, что вас беспокоит\n"
                "• Сменить тему — отправьте \n/change_theme\n"
                "• Посмотреть команды — отправьте /help\n\n"
                "Я здесь, чтобы помочь. Расскажите, что происходит."
            )
        )
    else:
        reply_kb = InlineKeyboardBuilder()
        reply_kb.row(
            MessageButton(text="Путь"),
            MessageButton(text="Консультации"),
            MessageButton(text="Теория"),
            MessageButton(text="Мировоззрение")
        )

        await context.set_state(ThemeChoice.first_choice)
        await bot.send_message(
            user_id=user_id,
            text=(
                f"👋 Привет!\n\n"
                "Я — AI-ассистент, обученный на материалах практикующего психолога.\n"
                "Моя задача — задавать вопросы, помогать разобраться в ситуации и искать решения вместе с вами.\n\n"
                "📌 **Что делать дальше?**\n"
                "1️⃣ Выберите тему из списка ниже\n"
                "2️⃣ Напишите, что вас беспокоит\n"
                "3️⃣ Я буду задавать уточняющие вопросы и предлагать гипотезы\n\n"
                "🔽 **Темы для работы:**\n"
                "• Путь — личная история эксперта, примеры и аналогии\n"
                "• Консультации — примеры из реальной практики\n"
                "• Теория — профессиональные концепции\n"
                "• Мировоззрение — актуальные взгляды эксперта\n\n"
                "ℹ️ Чтобы увидеть список команд, отправьте /help"
            ),
            attachments=[reply_kb.as_markup()]
        )

@dp.message_created(ThemeChoice.first_choice)
async def theme_choice_handler(event: MessageCreated, context: MemoryContext):
    await context.update_data(first_choice=event.message.body.text)

    data = await context.get_data()
    data_choice = data['first_choice']
    user_id = event.from_user.user_id

    try:
        new_session = await MaxService.create_session(user_id, data_choice)

        await context.set_state(None)

        await bot.send_message(user_id=user_id,
                               text=(
                                    f"✅ Тема выбрана: **{data_choice}**\n\n"
                                    "Теперь просто напишите, что вас беспокоит.\n"
                                    "Я буду задавать уточняющие вопросы и предлагать гипотезы.\n\n"
                                    "🔁 Если захотите сменить тему — отправьте /change_theme\n"
                                    "📌 Чтобы отметить важное сообщение — отправьте /mark\n"
                                    "📞 Чтобы записаться на консультацию — отправьте /consult"
                                ),
                               )
    except Exception as e:
        await bot.send_message(user_id=user_id,
                               text=f"Ошибка на стороне сервера",
                               )

@dp.message_created(F.message.body.text)
async def handle_message(event: MessageCreated, context: MemoryContext):
    user_id = event.from_user.user_id
    text = event.message.body.text
    if text.startswith('/'):
        return

    session = await MaxService.get_session(user_id)
    selected_topic = session.topic
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

    already_request = await MaxService.get_request(user_id)
    if answer:

        last_exchange = f"Клиент: {text}\n\nБот: {answer}"
        await context.update_data(
            last_exchange=last_exchange,
            last_topic=selected_topic
        )

        await MaxService.add_message(user_id, "assistant", answer)

        await context.update_data(
            last_exchange=f"Клиент: {text}\n\nБот: {answer}",
            last_topic=selected_topic
        )

        await bot.send_message(user_id=user_id, text=answer)
    else:
        await bot.send_message(
            user_id=user_id,
            text="⚠️ Не удалось получить ответ. Попробуйте позже."
        )



async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())