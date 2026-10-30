import datetime
from urllib.parse import urlparse

from vkbottle import Formatter
from vkbottle.bot import Message, BotLabeler, MessageEvent
from vkbottle_types import GroupEventType

from src.logger_config import setup_logger
from src.vk_bot.admin_handler.repository import VkAdminRepository
from src.vk_bot.bot_instance import bot, labeler
from src.vk_bot.keyboards import admin_back
from src.vk_bot.models import AdminStates
from src.vk_bot.repository import VkFactRepository

logger = setup_logger('fact_handler_vk', 'vk', 'fact_handler_vk.log')

# @fact_labeler.message(payload={"action": "fact"})
# async def send_fact(message: Message):
#     user_id = message.from_id
#
#     try:
#         exists_user = await VkUserRepository.get_user(user_id)
#         logger.info(f"Получение пользователя VK {user_id}")
#
#         if not exists_user:
#             logger.warning(f"Пользователь не {user_id} не создан. Создание")
#             user_info = await message.get_user()
#             first_name = user_info.first_name
#             await VkUserRepository.create_user(user_id, first_name)
#
#         now = datetime.datetime.now()
#         if exists_user.last_fact_date:
#             time_diff = now - exists_user.last_fact_date
#             if time_diff.total_seconds() < 86400:
#                 logger.info(f"Пользователь {user_id} уже просматривал ежедневный факт")
#                 return await message.answer(
#                     "Ты уже видел факт дня сегодня! Возвращайся завтра 😉",
#                     keyboard=get_main_menu()
#                 )
#
#         random_fact = await VkFactRepository.get_random_fact()
#         if not random_fact:
#             return await message.answer("Пока фактов нет. Загляни позже!")
#
#         await VkUserRepository.update_last_fact_date(user_id)
#         logger.info(f"Обновление статуса - последний прсомотр факта дня у пользоватея {user_id}")
#
#         await message.answer(
#             Formatter("{:bold}:\n\n{}").format("💡 Факт дня", random_fact.title),
#             keyboard=get_video_and_back_keyboard(random_fact.video_url)
#         )
#
#     except Exception as e:
#         logger.info(f"Пользователь {user_id} получил неизвестную ошибку: {e}")
#         await message.answer(f"Неизвестная ошибка")

@labeler.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
async def start_create_fact(message: MessageEvent):
    if message.payload.get("action") != "create_fact":
        return

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

@labeler.message(state=AdminStates.WAITING_FOR_FACT_TEXT)
async def get_fact_text(message: Message):
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
            AdminStates.WAITING_FOR_FACT_VIDEO,
            fact_title=message.text
        )

        await message.answer(
            f"Введите ссылку для просмотра материала: ")

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.send_message(f"Неизвестная ошибка")

@labeler.message(state=AdminStates.WAITING_FOR_FACT_VIDEO)
async def save_fact(message: Message):
    user_id = message.from_id

    try:
        payload = message.state_peer.payload
        fact_title = payload.get("fact_title")
        url = message.text

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

        await VkFactRepository.create_fact(fact_title, url)
        logger.info(f"Админ {user_id} успешно создал факт: {fact_title} - {url}")
        await bot.state_dispenser.delete(message.from_id)

        await message.answer(
            f"Факт успешно создан:\n Название факта: {fact_title}\n Ссылка: {url}",
            keyboard=admin_back())

    except Exception as e:
        logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
        await message.send_message(f"Неизвестная ошибка")
