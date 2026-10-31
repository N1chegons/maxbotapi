from urllib.parse import urlparse
from vkbottle.bot import Message

from src.logger_config import setup_logger
from src.vk_bot.admin_handler.repository import VkAdminRepository
from src.vk_bot.bot_instance import bot, labeler
from src.vk_bot.keyboards import admin_back
from src.vk_bot.models import AdminStates
from src.vk_bot.repository import VkTestRepository

logger = setup_logger('test_handler_vk', 'vk', 'test_handler_vk.log')

@labeler.message(state=AdminStates.WAITING_FOR_TEST_QUESTION)
async def get_test_text(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.peer_id)
        return await message.answer("Создание отменено.")

    try:
        exists_admin = VkAdminRepository.is_admin(user_id)
        if not exists_admin:
            return await message.answer("⛔ Вы не являетесь администратором.")

        await bot.state_dispenser.set(
            message.peer_id,
            AdminStates.WAITING_FOR_TEST_VIDEO,
            test_title=message.text
        )

        await message.answer(f"Введите ссылку для просмотра материала (Введите 'нет' - если нет ссылки): ")
    except Exception as e:
        logger.error(f"Админ {user_id} получил ошибку: {e}")
        await message.answer("Неизвестная ошибка")


@labeler.message(state=AdminStates.WAITING_FOR_TEST_VIDEO)
async def save_test(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.peer_id)
        return await message.answer("Создание отменено.")

    try:
        payload = message.state_peer.payload
        test_title = payload.get("test_title")
        url = message.text if message.text.lower() != 'нет' else None

        if url:
            parsed_url = urlparse(url)
            if not parsed_url.netloc:
                return await message.answer("❌ Неверный формат ссылки. Отправь еще раз или напиши 'нет'.")

        await VkTestRepository.create_test(test_title, url)
        logger.info(f"Админ {user_id} успешно создал тест: {test_title} - {url}")

        await bot.state_dispenser.delete(message.peer_id)

        await message.answer(
            f"✅ Игра успешно создана!\n\nОписание: {test_title}\n Ссылка: {url}",
            keyboard=admin_back()
        )

    except Exception as e:
        logger.error(f"Админ {user_id} получил ошибку: {e}")
        await message.answer(f"Неизвестная ошибка: {e}")