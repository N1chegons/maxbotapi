from vkbottle.bot import MessageEvent
from vkbottle_types import GroupEventType

from src.logger_config import setup_logger
from src.vk_bot.admin_handler.repository import VkAdminRepository
from src.vk_bot.bot_instance import bot, labeler
from src.vk_bot.models import AdminStates

logger = setup_logger('message_event', 'vk', 'message_event.log')

@labeler.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
async def start_create(message: MessageEvent):
    payload = message.object.payload
    if payload["action"] == "create_fact":
        user_id = message.user_id
        logger.info(f"Админ {user_id} начал создание факта.")

        try:
            exists_admin = VkAdminRepository.is_admin(user_id)
            if not exists_admin:
                logger.info(f"Пользователь {user_id} не является админом")
                await message.answer(
                    "⛔ Вы не являетесь администратором. Доступ запрещен."
                )


            await bot.state_dispenser.set(message.peer_id, AdminStates.WAITING_FOR_FACT_TEXT)
            await message.send_message("Введите название факта (Если хотите отменить начатое действие напишите - 'отмена'):")

        except Exception as e:
            logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
            await message.send_message(f"Неизвестная ошибка")

    if payload["action"] == "create_opinion":
        user_id = message.user_id
        logger.info(f"Админ {user_id} начал создание сбора мнений.")

        try:
            exists_admin = VkAdminRepository.is_admin(user_id)
            if not exists_admin:
                logger.info(f"Пользователь {user_id} не является админом")
                await message.answer(
                    "⛔ Вы не являетесь администратором. Доступ запрещен."
                )

            await bot.state_dispenser.set(message.peer_id, AdminStates.WAITING_FOR_OPINION_TEXT)
            await message.send_message("Введите заголовок сбора мнения (Если хотите отменить начатое действие напишите - 'отмена'):")

        except Exception as e:
            logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
            await message.send_message(f"Неизвестная ошибка")

    if payload["action"] == "create_test":
        user_id = message.user_id
        logger.info(f"Админ {user_id} начал создание теста.")

        try:
            exists_admin = VkAdminRepository.is_admin(user_id)
            if not exists_admin:
                logger.info(f"Пользователь {user_id} не является админом")
                await message.answer(
                    "⛔ Вы не являетесь администратором. Доступ запрещен."
                )

            await bot.state_dispenser.set(message.peer_id, AdminStates.WAITING_FOR_TEST_QUESTION)
            await message.send_message("Введите вопрос теста (Если хотите отменить начатое действие напишите - 'отмена'):")

        except Exception as e:
            logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
            await message.send_message(f"Неизвестная ошибка")