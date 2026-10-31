from urllib.parse import urlparse

from vkbottle.bot import Message

from src.logger_config import setup_logger
from src.vk_bot.admin_handler.repository import VkAdminRepository
from src.vk_bot.bot_instance import bot, labeler
from src.vk_bot.keyboards import admin_back
from src.vk_bot.models import AdminStates
from src.vk_bot.repository import VkFactRepository, VkRiddleRepository

logger = setup_logger('riddle_handler_vk', 'vk', 'riddle_handler_vk.log')

# created
@labeler.message(state=AdminStates.WAITING_FOR_RIDDLE_TEXT)
async def get_riddle_text(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.from_id)
        return await message.answer("Создание отменено.")

    try:
        payload = message.state_peer.payload.get("riddle_title")

        exists_admin = VkAdminRepository.is_admin(user_id)
        if not exists_admin:
            logger.info(f"Пользователь {user_id} не является админом")
            await message.answer(
                "⛔ Вы не являетесь администратором. Доступ запрещен."
            )

        await bot.state_dispenser.set(
            message.peer_id,
            AdminStates.WAITING_FOR_RIDDLE_VIDEO,
            riddle_title=message.text
        )

        await message.answer(
            f"Введите ссылку для просмотра материала  (Введите 'нет' - если нет ссылки): ")

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.send_message(f"Неизвестная ошибка")

@labeler.message(state=AdminStates.WAITING_FOR_RIDDLE_VIDEO)
async def save_riddle(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.from_id)
        return await message.answer("Создание отменено.")

    try:
        payload = message.state_peer.payload
        riddle_title = payload.get("riddle_title")
        url = message.text if message.text.lower() != 'нет' else None

        if url is not None:
            parsed_url = urlparse(url)
            if not parsed_url.netloc:
                return await message.answer(
                    "❌ Ошибка: неверный формат ссылки. Проверьте, что вы отправили полный адрес."
                )

        exists_admin = VkAdminRepository.is_admin(user_id)
        if not exists_admin:
            logger.info(f"Пользователь {user_id} не является админом")
            await message.answer(
                "⛔ Вы не являетесь администратором. Доступ запрещен."
            )

        await VkRiddleRepository.create_riddle(riddle_title, url)
        logger.info(f"Админ {user_id} успешно создал загадку: {riddle_title} - {url}")
        await bot.state_dispenser.delete(message.from_id)

        await message.answer(
            f"Загадка успешно создана:\n Текст загадки: {riddle_title}\n Ссылка: {url}",
            keyboard=admin_back())

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.send_message(f"Неизвестная ошибка")


# edited
@labeler.message(state=AdminStates.WAITING_FOR_EDIT_RIDDLE_TEXT)
async def get_new_riddle_text(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.peer_id)
        return await message.answer("Отменено.", keyboard=admin_back())

    try:
        payload = message.state_peer.payload
        riddle_id = payload.get("edit_riddle_id")

        exist_fact = await VkRiddleRepository.get_riddle_by_id(riddle_id)
        new_text = ""

        if message.text.lower() == 'нет':
            new_text += exist_fact.title

        new_text += message.text

        await bot.state_dispenser.set(
            message.peer_id,
            AdminStates.WAITING_FOR_EDIT_RIDDLE_VIDEO,
            edit_riddle_id=riddle_id,
            new_title=new_text
        )
        await message.answer("Теперь отправьте НОВУЮ ссылку на видео (или 'нет', чтобы оставить старую):")

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.answer(f"Неизвестная ошибка")

@labeler.message(state=AdminStates.WAITING_FOR_EDIT_RIDDLE_VIDEO)
async def get_new_riddle_video(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.peer_id)
        return await message.answer("Отменено.", keyboard=admin_back())

    try:
        payload = message.state_peer.payload
        fact_id = payload.get("edit_riddle_id")
        new_text = payload.get("new_title")

        exist_fact = await VkRiddleRepository.get_riddle_by_id(fact_id)
        new_video = ""

        if message.text.lower() == 'нет':
            new_video += exist_fact.video_url

        new_video += message.text

        await VkRiddleRepository.update_riddle(fact_id, new_text, new_video)
        logger.info(f"Админ {user_id} успешно обновил загадку ID {fact_id}: {new_text} - {new_video}")
        await bot.state_dispenser.delete(message.peer_id)

        await message.answer(
            f"✅ Загадка обновлена!\n\nНовый текст: {new_text}\nНовая ссылка: {new_video}",
            keyboard=admin_back()
        )

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.answer(f"Неизвестная ошибка")