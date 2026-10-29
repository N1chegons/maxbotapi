import random
from vkbottle.bot import Message, BotLabeler

from src.vk_bot.keyboards import get_video_and_back_keyboard

fact_labeler = BotLabeler()

# Пока используем заглушку. Потом заменим на запрос к базе данных.
FAKE_FACTS = [
    {
        "text": "Какой-то факт",
        "video_url": "https://vk.com/video-123456_456239017"
    },
    {
        "text": "Какой-то факт",
        "video_url": "https://vk.com/video-123456_456239018"
    }
]


@fact_labeler.message(payload={"action": "fact"})
async def send_fact(message: Message):
    fact = random.choice(FAKE_FACTS)

    await message.answer(
        f"💡 Факт дня:\n\n{fact['text']}",
        keyboard=get_video_and_back_keyboard(fact['video_url'])
    )