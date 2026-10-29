from vkbottle.bot import Message, BotLabeler

from src.vk_bot.keyboards import get_main_menu

menu_labeler = BotLabeler()

@menu_labeler.message(text=["/start", "Начать", "start"])
async def start_handler(message: Message):
    await message.answer(
        "Привет! Я бот-помощник. Выбирай, что хочешь узнать сегодня:",
        keyboard=get_main_menu()
    )

@menu_labeler.message(payload={"action": "back_to_menu"})
async def back_to_menu_handler(message: Message):
    await message.answer(
        "Главное меню:",
        keyboard=get_main_menu()
    )