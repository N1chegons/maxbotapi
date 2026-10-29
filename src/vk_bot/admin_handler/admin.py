import random
from vkbottle.bot import Message, BotLabeler

from src.logger_config import setup_logger
from src.vk_bot.admin_handler.repository import VkAdminRepository
from src.vk_bot.keyboards import get_admin_menu

admin_labeler = BotLabeler()
logger = setup_logger('admin_handler_vk', 'vk', 'admin_handler_vk.log')

@admin_labeler.message(text=["/admin", "Админ", "admin"])
async def admin_panel(message: Message):
    try:
        user_id = message.from_id
        exists_admin = VkAdminRepository.is_admin(user_id)
        logger.info(f"Получение админа VK {user_id}")

        if not exists_admin:
            logger.info(f"Пользователь {user_id} не является админом")
            await message.answer(
                "Вы не являетесь администратором. Доступ запрещен"
            )

        await message.answer(
            "Вы в панели администратора.\nВыберите действия на кнпоках.",
            keyboard=get_admin_menu()
        )

    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        pass