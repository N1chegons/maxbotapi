from urllib.parse import urlparse

from vkbottle.bot import Message

from src.logger_config import setup_logger
from src.vk_bot.admin_handler.repository import VkAdminRepository
from src.vk_bot.bot_instance import bot, labeler
from src.vk_bot.keyboards import admin_back
from src.vk_bot.models import AdminStates
from src.vk_bot.repository import VkOpinionRepository

logger = setup_logger('opinions_handler_vk', 'vk', 'opinions_handler_vk.log')

# created
@labeler.message(state=AdminStates.WAITING_FOR_OPINION_TEXT)
async def get_opinion_text(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.from_id)
        return await message.answer("Создание отменено.")

    try:
        payload = message.state_peer.payload.get("fact_title")

        exists_admin = VkAdminRepository.is_admin(user_id)
        if not exists_admin:
            logger.info(f"Пользователь {user_id} не является админом")
            await message.answer(
                "⛔ Вы не являетесь администратором. Доступ запрещен."
            )

        await bot.state_dispenser.set(
            message.peer_id,
            AdminStates.WAITING_FOR_OPINION_VIDEO,
            opinion_title=message.text
        )

        await message.answer(f"Введите ссылку для просмотра материала  (Введите 'нет' - если нет ссылки): ")

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.answer(f"Неизвестная ошибка")

@labeler.message(state=AdminStates.WAITING_FOR_OPINION_VIDEO)
async def save_opinion(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.from_id)
        return await message.answer("Создание отменено.")

    try:
        payload = message.state_peer.payload
        opinion_title = payload.get("opinion_title")
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

        await VkOpinionRepository.create_opinion(opinion_title, url)
        logger.info(f"Админ {user_id} успешно создал сбор мнений: {opinion_title} - {url}")

        await bot.state_dispenser.delete(message.from_id)

        await message.answer(
            f"Сбор мнений успешно создан:\n Заголовок сбора: {opinion_title}\n Ссылка: {url}",
            keyboard=admin_back())

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.answer(f"Неизвестная ошибка")

# updated
@labeler.message(state=AdminStates.WAITING_FOR_EDIT_OPINION_TEXT)
async def get_new_opinion_text(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.peer_id)
        return await message.answer("Отменено.", keyboard=admin_back())

    try:
        payload = message.state_peer.payload
        opinion_id = payload.get("edit_opinion_id")

        exist_opinion = await VkOpinionRepository.get_opinion_by_id(opinion_id)
        new_text = ""

        if message.text.lower() == 'нет':
            new_text += exist_opinion.title

        new_text += message.text

        await bot.state_dispenser.set(
            message.peer_id,
            AdminStates.WAITING_FOR_EDIT_OPINION_VIDEO,
            edit_opinion_id=opinion_id,
            new_title=new_text
        )
        await message.answer("Теперь отправьте НОВУЮ ссылку на видео (или 'нет', чтобы оставить старую):")

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.answer(f"Неизвестная ошибка")

@labeler.message(state=AdminStates.WAITING_FOR_EDIT_OPINION_VIDEO)
async def get_new_opinion_video(message: Message):
    user_id = message.from_id

    if message.text.lower() == 'отмена':
        await bot.state_dispenser.delete(message.peer_id)
        return await message.answer("Отменено.", keyboard=admin_back())

    try:
        payload = message.state_peer.payload
        opinion_id = payload.get("edit_opinion_id")
        new_text = payload.get("new_title")

        exist_opinion = await VkOpinionRepository.get_opinion_by_id(opinion_id)
        new_video = ""

        if message.text.lower() == 'нет':
            new_video += exist_opinion.video_url

        new_video += message.text

        await VkOpinionRepository.update_opinion(opinion_id, new_text, new_video)
        logger.info(f"Админ {user_id} успешно обновил сбор ID {opinion_id}: {new_text} - {new_video}")

        await bot.state_dispenser.delete(message.peer_id)

        await message.answer(
            f"✅ Сбор обновлен!\n\nНовый текст: {new_text}\nНовая ссылка: {new_video}",
            keyboard=admin_back()
        )

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.answer(f"Неизвестная ошибка")