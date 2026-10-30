from vkbottle.bot import Message, BotLabeler

from src.logger_config import setup_logger
from src.vk_bot.keyboards import get_admin_menu
from src.vk_bot.repository import VkUserRepository

menu_labeler = BotLabeler()
logger = setup_logger('menu_handler', 'vk', 'menu_handler_work.log')

@menu_labeler.message(text=["/start", "Начать", "start"])
async def start_handler(message: Message):
    try:
        user_id = message.from_id
        exists_user = await VkUserRepository.get_user(user_id)
        logger.info(f"Получение пользователя VK {user_id}")

        if not exists_user:
            logger.warning(f"Пользователь не {user_id} не создан. Создание")
            user_info = await message.get_user()
            first_name = user_info.first_name
            await VkUserRepository.create_user(user_id, first_name)

        if message.ref:
            logger.info(f"Пользователь {message.from_id} пришел по ссылке с меткой: {message.ref}")

            if message.ref == "opinion":
                await message.answer(
                    "Привет! Вижу, ты хочешь высказать мнение. Напиши его сюда."
                    # keyboard=get_main_menu()
                )
                return

        await message.answer(
            "Привет! Я бот-помощник. Выбирай, что хочешь узнать сегодня."
            # keyboard=get_main_menu()
        )

    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        pass

# @menu_labeler.message(payload={"action": "back_to_menu"})
# async def back_to_menu_handler(message: Message):
#     await message.answer(
#         "Вы в главном меню.",
#         keyboard=get_main_menu()
#     )

@menu_labeler.message(payload={"action": "back_to_admin_menu"})
async def back_to_admin_menu_handler(message: Message):
    await message.answer(
        "Вы в панели администратора.",
        keyboard=get_admin_menu()
    )