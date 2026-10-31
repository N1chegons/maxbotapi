from vkbottle import Keyboard, Callback, KeyboardButtonColor, Text
from vkbottle.bot import MessageEvent
from vkbottle_types import GroupEventType

from src.logger_config import setup_logger
from src.vk_bot.admin_handler.repository import VkAdminRepository
from src.vk_bot.bot_instance import bot, labeler
from src.vk_bot.models import AdminStates
from src.vk_bot.repository import VkFactRepository, VkOpinionRepository, VkRiddleRepository

logger = setup_logger('message_event', 'vk', 'message_event.log')

@labeler.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
async def start_create(message: MessageEvent):
    payload = message.object.payload

    # create
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
            await message.send_message("Введите описание факта (Если хотите отменить начатое действие напишите - 'отмена'):")

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
            await message.send_message("Введите описание игры (Если хотите отменить начатое действие напишите - 'отмена'):")

        except Exception as e:
            logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
            await message.send_message(f"Неизвестная ошибка")

    if payload["action"] == "create_riddle":
        user_id = message.user_id
        logger.info(f"Админ {user_id} начал создание загадки.")

        try:
            exists_admin = VkAdminRepository.is_admin(user_id)
            if not exists_admin:
                logger.info(f"Пользователь {user_id} не является админом")
                await message.answer(
                    "⛔ Вы не являетесь администратором. Доступ запрещен."
                )

            await bot.state_dispenser.set(message.peer_id, AdminStates.WAITING_FOR_RIDDLE_TEXT)
            await message.send_message("Введите вопрос загадки (Если хотите отменить начатое действие напишите - 'отмена'):")

        except Exception as e:
            logger.info(f"Админ {user_id} получил неизвестную ошибку: {e}")
            await message.send_message(f"Неизвестная ошибка")

    # update
    if payload["action"] == "edit_fact":

        facts = await VkFactRepository.get_facts_list(limit=9)
        if not facts:
            return await message.answer("Фактов нет.")

        text = ""
        if not facts:
            text += "На данный момент фактов нету.\n"
        else:
            for fact in facts:
                text += f"💡 Факт №{fact.id}:\n--> Описание: {fact.title[:20]}...\n\n"


        keyboard = Keyboard(inline=True)
        c = 0
        for f in facts:
            c += 1
            keyboard.add(
                Callback(f"ID {f.id}", payload={"action": "edit_this_fact", "fact_id": f.id}),
                color=KeyboardButtonColor.SECONDARY
            )

            if c % 3 == 0:
                keyboard.row()

        if c % 3 != 0:
            keyboard.row()

        keyboard.add(Text("↩️ В меню", payload={"action": "back_to_admin_menu"}), color=KeyboardButtonColor.SECONDARY)

        await message.send_message(f"Последние факты:\n{text}\n\nВыберите на кнопках номер факта для редактирования:", keyboard=keyboard.get_json())

    if payload["action"] == "edit_this_fact":
        fact_id = payload["fact_id"]

        await bot.state_dispenser.set(message.peer_id, AdminStates.WAITING_FOR_EDIT_FACT_TEXT, edit_fact_id=fact_id)
        await message.send_message("Введите НОВЫЙ текст факта (или напишите 'нет', чтобы оставить старый, 'отмена' - если хотите отменить начатое действие):")

    if payload["action"] == "edit_opinion":

        opinions = await VkOpinionRepository.get_opinions_list(limit=9)
        if not opinions:
            return await message.answer("Сборов нет.")

        text = ""
        if not opinions:
            text += "На данный момент сборов мнений нету.\n"
        else:
            for fact in opinions:
                text += f"💬 Сбор №{fact.id}:\n--> Описание: {fact.title[:20]}...\n\n"

        keyboard = Keyboard(inline=True)
        c = 0
        for f in opinions:
            c += 1
            keyboard.add(
                Callback(f"ID {f.id}", payload={"action": "edit_this_opinion", "opinion_id": f.id}),
                color=KeyboardButtonColor.SECONDARY
            )

            if c % 3 == 0:
                keyboard.row()

        if c % 3 != 0:
            keyboard.row()

        keyboard.add(Text("↩️ В меню", payload={"action": "back_to_admin_menu"}), color=KeyboardButtonColor.SECONDARY)

        await message.send_message(f"Последние сборы:\n{text}\n\nВыберите на кнопках номер сбора мнения для редактирования:",
                                   keyboard=keyboard.get_json())

    if payload["action"] == "edit_this_opinion":
        opinion_id = payload["opinion_id"]

        await bot.state_dispenser.set(message.peer_id, AdminStates.WAITING_FOR_EDIT_OPINION_TEXT, edit_opinion_id=opinion_id)
        await message.send_message("Введите НОВЫЙ заголовок сбора (или напишите 'нет', чтобы оставить старый, 'отмена' - если хотите отменить начатое действие):")

    if payload["action"] == "edit_riddle":

        riddles = await VkRiddleRepository.get_riddle_list(limit=9)
        if not riddles:
            return await message.answer("Загадок нет.")

        text = ""
        if not riddles:
            text += "На данный момент загадок нету.\n"
        else:
            for fact in riddles:
                text += f"🧩 Загадка №{fact.id}:\n--> Описание: {fact.title[:20]}...\n\n"

        keyboard = Keyboard(inline=True)
        c = 0
        for f in riddles:
            c += 1
            keyboard.add(
                Callback(f"ID {f.id}", payload={"action": "edit_this_riddle", "riddle_id": f.id}),
                color=KeyboardButtonColor.SECONDARY
            )

            if c % 3 == 0:
                keyboard.row()

        if c % 3 != 0:
            keyboard.row()

        keyboard.add(Text("↩️ В меню", payload={"action": "back_to_admin_menu"}), color=KeyboardButtonColor.SECONDARY)

        await message.send_message(f"Последние загадки:\n{text}\n\nВыберите на кнопках номер загадки для редактирования:",
                                   keyboard=keyboard.get_json())

    if payload["action"] == "edit_this_riddle":
        riddle_id = payload["riddle_id"]

        await bot.state_dispenser.set(message.peer_id, AdminStates.WAITING_FOR_EDIT_RIDDLE_TEXT, edit_riddle_id=riddle_id)
        await message.send_message("Введите НОВЫЙ вопрос загадки (или напишите 'нет', чтобы оставить старый, 'отмена' - если хотите отменить начатое действие):")

