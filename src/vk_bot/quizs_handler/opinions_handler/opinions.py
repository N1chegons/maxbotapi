from urllib.parse import urlparse

from vkbottle.bot import Message

from src.logger_config import setup_logger
from src.vk_bot.admin_handler.repository import VkAdminRepository
from src.vk_bot.bot_instance import bot, labeler
from src.vk_bot.keyboards import admin_back
from src.vk_bot.models import AdminStates
from src.vk_bot.repository import VkOpinionRepository

logger = setup_logger('opinions_handler_vk', 'vk', 'opinions_handler_vk.log')

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
