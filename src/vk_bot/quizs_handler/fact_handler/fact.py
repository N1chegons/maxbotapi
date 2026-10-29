import random
from vkbottle.bot import Message, BotLabeler, MessageEvent
from vkbottle_types import GroupEventType

from src.logger_config import setup_logger
from src.vk_bot.admin_handler.repository import VkAdminRepository
from src.vk_bot.bot_instance import bot
from src.vk_bot.keyboards import admin_back
from src.vk_bot.models import AdminStates
from src.vk_bot.repository import VkFactRepository

fact_labeler = BotLabeler()

logger = setup_logger('fact_handler_vk', 'vk', 'fact_handler_vk.log')

@fact_labeler.message(payload={"action": "fact"})
async def send_fact(message: Message):
    try:
        await message.answer(
            "Факт дня"
            # f"💡 Факт дня:\n\n{fact['text']}",
            # keyboard=get_video_and_back_keyboard(fact['video_url'])
        )
    except Exception as e:
        await message.answer(
            "Неизвестная ошибка"
        )
        pass


@fact_labeler.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
async def start_create_fact(message: MessageEvent):
    user_id = message.user_id

    try:
        exists_admin = VkAdminRepository.is_admin(user_id)
        if not exists_admin:
            logger.info(f"Пользователь {user_id} не является админом")
            await message.answer(
                "⛔ Вы не являетесь администратором. Доступ запрещен"
            )


        await bot.state_dispenser.set(message.peer_id, AdminStates.WAITING_FOR_FACT_TEXT)
        await message.send_message("Введите название факта (Если хотите отменить начатое действие напишите - 'отмена'):")

    except Exception as e:
        await message.send_message(f"Неизвестная ошибка: {e}")


@fact_labeler.message(state=AdminStates.WAITING_FOR_FACT_TEXT)
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
                "⛔ Вы не являетесь администратором. Доступ запрещен"
            )

        await bot.state_dispenser.set(
            message.peer_id,
            AdminStates.WAITING_FOR_FACT_VIDEO,
            fact_title=message.text
        )

        await message.answer(
            f"Введите ссылку для просмотра материала: ",
            keyboard=admin_back())

    except Exception as e:
        await message.answer(f"Неизвестная ошибка: {e}")


@fact_labeler.message(state=AdminStates.WAITING_FOR_FACT_VIDEO)
async def save_fact(message: Message):
    user_id = message.from_id

    try:
        payload = message.state_peer.payload
        fact_title = payload.get("fact_title")
        url = message.text

        exists_admin = VkAdminRepository.is_admin(user_id)
        if not exists_admin:
            logger.info(f"Пользователь {user_id} не является админом")
            await message.answer(
                "⛔ Вы не являетесь администратором. Доступ запрещен"
            )

        await VkFactRepository.create_fact(fact_title, url)
        await bot.state_dispenser.delete(message.from_id)

        await message.answer(
            f"Факт {fact_title} с ссылкой {url} - создан.",
            keyboard=admin_back())

    except Exception as e:
        await message.answer(f"Неизвестная ошибка: {e}")
