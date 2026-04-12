import asyncio
import logging

from maxapi import Bot, Dispatcher, F
from maxapi.context import MemoryContext
from maxapi.filters.command import Command
from maxapi.types import MessageCreated, BotStarted, MessageButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from src.config import settings
from src.max.models import ThemeChoice, ConsultChoice
from src.max.repository import MaxService
from src.yandexai.config import THEMES_INDEXES
from src.yandexai.orchestrator import ask_ai_with_index


logging.basicConfig(level=logging.INFO)
TOKEN = settings.MAX_BOT_TOKEN

bot = Bot(TOKEN)
dp = Dispatcher()

# Command
@dp.message_created(Command('new'))
async def new_theme(event: MessageCreated, context: MemoryContext):
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

@dp.message_created(Command('igor'))
async def igor_command(event: MessageCreated,  context: MemoryContext):
    user_id = event.from_user.user_id
    username = event.from_user.username

    already_request = await MaxService.get_request(user_id)
    if already_request:
        await bot.send_message(
            user_id=user_id,
            text="✔️ Вы уже отправили заявку на консультацию!\n\nВы можете продолжить задавать вопросы."
        )

    else:
        reply_kb = InlineKeyboardBuilder()
        reply_kb.row(
            MessageButton(text="✅ ДА"),
            MessageButton(text="❌ НЕТ"),
        )

        await context.set_state(ConsultChoice.ant_choice)

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

@dp.message_created(Command('mark'))
async def mark_command(event: MessageCreated, context: MemoryContext):
    user_id = event.from_user.user_id

    data = await context.get_data()
    last_exchange = data.get("last_exchange")
    last_topic = data.get("last_topic")

    if not last_exchange:
        await bot.send_message(
            user_id=user_id,
            text="⚠️ Нет сообщений для отметки. Сначала задайте вопрос."
        )
        return

    await MaxService.add_feedback(
        client_id=user_id,
        fragment=last_exchange,
        is_positive=True,
        session_topic=last_topic
    )

    await bot.send_message(
        user_id=user_id,
        text="✔️ Спасибо за похвалу. Эксперт увидит что вы меня похвалили.\n"
             "Можете продолжить диалог."
    )

@dp.message_created(Command('hren'))
async def hren_command(event: MessageCreated, context: MemoryContext):
    user_id = event.from_user.user_id

    data = await context.get_data()
    last_exchange = data.get("last_exchange")
    last_topic = data.get("last_topic")

    if not last_exchange:
        await bot.send_message(
            user_id=user_id,
            text="⚠️ Нет сообщений для отметки. Сначала задайте вопрос."
        )
        return

    await MaxService.add_feedback(
        client_id=user_id,
        fragment=last_exchange,
        is_positive=False,
        session_topic=last_topic
    )

    await bot.send_message(
        user_id=user_id,
        text="✔️ Думаю что сделал что-то не так. Эксперт увидит что вы меня поругали.\n"
             "Можете продолжить диалог."
    )


@dp.message_created(Command('help'))
async def help_command(event: MessageCreated):
    user_id = event.from_user.user_id

    help_text = (
            "📋 **Доступные команды**\n\n"
            "🔹 /new — сменить тему консультации (Путь, Консультации, Теория, Мировоззрение)\n"
            "🔹 /mark — похвалить бота (попадёт в отчёт эксперту)\n"
            "🔹 /hren - поругать бота (попадёт в отчёт эксперту)\n"
            "🔹 /igor — записаться на личную консультацию к эксперту\n"
            "🔹 /help — показать список команд\n\n"
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

# logic
@dp.bot_started()
async def bot_started(event: BotStarted, context: MemoryContext):
    user_id = event.user.user_id

    already_topic = await MaxService.get_session(user_id)

    if already_topic:
        await bot.send_message(
            user_id=user_id,
            text=(
                f"👋 С возвращением!\n\n"
                f"Вспомни, на какой теме ты остановился или спроси меня 😊"
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
                "👋 Привет! Ты находишься в виртуальной приёмной Игоря Неповинных 😉\n"
                "Я не знаю кто ты, но могу помочь раскрутить пару гипотез в голове.\n"
                "Узнай кто я (путь) и задай вопрос (консультация). Переписка нигде не сохраняется кроме твоего гаджета 📱\n\n"
                "На консультации я задам тебе уточняющие вопросы, которые прояснят проблему и помогут принять верное решение.\n"
                "Дай проблеме повариться в диалоге и результат тебя удивит 😯.\n"
                "Если тебе понравится, что я говорю: похвали меня (напиши /mark отдельным сообщением). Если скажу фигню, то поругай (/hren).\n\n"
                "🧠 Если психика тебя интересует с научной точки зрения, то изучи мои взгляды на современную психологию (теория).\n"
                "Если тебя интересует будущее России и мира в целом, то заходи в мировоззрение 🚀.\n\n"
                "Здесь ты можешь обрести спокойствие 😌"
            ),
            attachments=[reply_kb.as_markup()]
        )

# --Theme choice
@dp.message_created(ThemeChoice.first_choice)
async def theme_choice_handler(event: MessageCreated, context: MemoryContext):
    await context.update_data(first_choice=event.message.body.text)

    data = await context.get_data()
    data_choice = data['first_choice']
    user_id = event.from_user.user_id

    try:
        new_session = await MaxService.create_session(user_id, data_choice)

        await context.set_state(None)

        if data_choice == "Путь":
            text = (
                "Добро пожаловать на мой путь 😊\n"
                "Задавай биографические вопросы и получай ответ❗\n\n"
                "Чтобы поменять тему напиши команду /new"
            )
        elif data_choice == "Консультации":
            text = (
                "Начинаем консультацию ❗\n\n"
                "Когда устанешь — напиши /new.\n\n"
                "Я ничего о тебе не знаю, запоминаю только похвалу (/mark) и критику (/hren).\n"
                "Мне важно, что ты думаешь прямо сейчас.\n\n"
                "Рассказывай, что тебя беспокоит? Какой вопрос хотел обсудить?"
            )
        elif data_choice == "Теория":
            text = (
                "Добро пожаловать в мир знаний и гипотез 😊\n\n"
                "Неповинных продолжает работу с теорией псилогики: шлифует, проверяет хитрые гипотезы.\n"
                "👍 Центральное положение защиты, самооценки и прогноза не вызывает сомнений.\n\n"
                "📚 Используй ИИ как справочник: задавай вопрос о прошлом психологии или её современном состоянии.\n"
                "🕰️ Узнай, зачем он создал псилогику и к чему пришёл за годы практики.\n\n"
                "Чтобы поменять тему — напиши /new"
            )
        elif data_choice == "Мировоззрение":
            text = (
                "Ты ступил на горячую землю с острыми темами 🔥\n\n"
                "Уходи, пока не захлестнули эмоции!\n"
                "Или ты готов к горячему диалогу?\n\n"
                "Чтобы поменять тему — напиши /new"
            )
        else:
            text = (f"Не могу понять тему: {data_choice}\n\n"
                    f"Пожайлуста выберите из приведенных ниже тем: Путь, Консультации, Теория, Мировоззрение")

        await bot.send_message(user_id=user_id, text=text)
    except Exception as e:
        await bot.send_message(user_id=user_id,
                               text=f"Ошибка на стороне сервера",
                               )

# --Consult
@dp.message_created(ConsultChoice.ant_choice)
async def igor_confirm(event: MessageCreated, context: MemoryContext):
    user_id = event.from_user.user_id
    answer = event.message.body.text.strip()




    if answer in ["✅ ДА", "ДА", "YES", "Да", "да"]:
        username = event.from_user.username or f"user_{user_id}"
        history = await MaxService.get_last_messages(user_id, limit=20)
        history_text = "\n".join([
            f"{'🧑 Клиент' if msg.role == 'user' else '🤖 Бот'}: {msg.content}"
            for msg in history
        ])

        await MaxService.add_request(
            client_id=user_id,
            contact=username,
            messages=history_text,
        )

        await bot.send_message(
            user_id=user_id,
            text="✔️ Заявка на консультацию отправлена❗\n\nВы можете продолжить вести диалог."
    )
    elif answer in ["❌ НЕТ", "НЕТ", "NO", "Нет", "нет"]:
        await bot.send_message(
            user_id=user_id,
            text="❌ Вы отменили заявку на консультацию.\n\nЕсли передумаешь — напиши `/igor` снова."
        )
    else:
        await bot.send_message(
            user_id=user_id,
            text="Пожалуйста, ответь ДА или НЕТ."
        )
        return

    # Сбрасываем состояние
    await context.set_state(None)

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