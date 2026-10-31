from urllib.parse import urlparse
from vkbottle.bot import Message

from src.logger_config import setup_logger
from src.vk_bot.admin_handler.repository import VkAdminRepository
from src.vk_bot.bot_instance import bot, labeler
from src.vk_bot.keyboards import admin_back
from src.vk_bot.models import AdminStates
from src.vk_bot.repository import VkTestRepository

logger = setup_logger('test_handler_vk', 'vk', 'test_handler_vk.log')

# created
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

        if url is not None:
            parsed_url = urlparse(url)
            if not parsed_url.netloc:
                return await message.answer("❌ Неверный формат ссылки. Отправь еще раз или напиши 'нет'.")

        await VkTestRepository.create_test(test_title, url)
        logger.info(f"Админ {user_id} успешно создал тест: {test_title} - {url}")

        await bot.state_dispenser.delete(message.peer_id)

        await message.answer(
            f"✅ Игра успешно создана!\n\nОписание: {test_title}\nСсылка: {url}",
            keyboard=admin_back()
        )

    except Exception as e:
        logger.error(f"Админ {user_id} получил ошибку: {e}")
        await message.answer(f"Неизвестная ошибка: {e}")

# updated
@labeler.message(state=AdminStates.WAITING_FOR_EDIT_TEST_TEXT)
async def get_new_test_text(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.peer_id)
        return await message.answer("Отменено.", keyboard=admin_back())

    try:
        payload = message.state_peer.payload
        test_id = payload.get("edit_test_id")

        exist_fact = await VkTestRepository.get_test_by_id(test_id)
        new_text = ""

        if message.text.lower() == 'нет':
            new_text += exist_fact.title

        new_text += message.text

        await bot.state_dispenser.set(
            message.peer_id,
            AdminStates.WAITING_FOR_EDIT_TEST_VIDEO,
            edit_test_id=test_id,
            new_title=new_text
        )
        await message.answer("Теперь отправьте НОВУЮ ссылку на видео (или 'нет', чтобы оставить старую):")

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.answer(f"Неизвестная ошибка")

@labeler.message(state=AdminStates.WAITING_FOR_EDIT_TEST_VIDEO)
async def get_new_test_video(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.peer_id)
        return await message.answer("Отменено.", keyboard=admin_back())

    try:
        payload = message.state_peer.payload
        test_id = payload.get("edit_test_id")
        new_text = payload.get("new_title")

        exist_fact = await VkTestRepository.get_test_by_id(test_id)
        new_video = ""

        if message.text.lower() == 'нет':
            new_video += exist_fact.video_url

        new_video += message.text

        await VkTestRepository.update_test(test_id, new_text, new_video)
        logger.info(f"Админ {user_id} успешно обновил загадку ID {test_id}: {new_text} - {new_video}")
        await bot.state_dispenser.delete(message.peer_id)

        await message.answer(
            f"✅ Тест обновлен!\n\nНовый текст: {new_text}\nНовая ссылка: {new_video}",
            keyboard=admin_back()
        )

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.answer(f"Неизвестная ошибка")