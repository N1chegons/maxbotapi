import random
from vkbottle.bot import Message, BotLabeler

from src.logger_config import setup_logger
from src.vk_bot.admin_handler.repository import VkAdminRepository
from src.vk_bot.bot_instance import labeler
from src.vk_bot.keyboards import get_admin_menu, get_admin_fact_menu, get_admin_riddle_menu, get_admin_opinions_menu, \
    get_admin_tests_menu
from src.vk_bot.repository import VkFactRepository, VkRiddleRepository, VkOpinionRepository, VkTestRepository

logger = setup_logger('admin_handler_vk', 'vk', 'admin_handler_vk.log')

@labeler.message(text=["/admin", "Админ", "admin"])
async def admin_panel(message: Message):
    try:
        user_id = message.from_id
        exists_admin = VkAdminRepository.is_admin(user_id)
        logger.info(f"Получение админа VK {user_id}")

        if not exists_admin:
            logger.info(f"Пользователь {user_id} не является админом")
            await message.answer(
                "⛔ Вы не являетесь администратором. Доступ запрещен"
            )

        await message.answer(
            "Вы в панели администратора.\nВыберите действия на кнпоках.",
            keyboard=get_admin_menu()
        )

    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        pass

@labeler.message(payload={"action": "menu_facts"})
async def admin_facts_menu(message: Message):
    try:
        user_id = message.from_id
        exists_admin = VkAdminRepository.is_admin(user_id)
        logger.info(f"Получение админа VK {user_id}")

        if not exists_admin:
            logger.info(f"Пользователь {user_id} не является админом")
            await message.answer(
                "⛔ Вы не являетесь администратором. Доступ запрещен"
            )

        facts_list = await VkFactRepository.get_facts_list()
        text = ""
        if not facts_list:
            text += "На данный момент фактов нету."
        else:
            for fact in facts_list:
                text += f"Факт №{fact.id}\n> Описание: {fact.title}\n> Ссылка: {fact.url}\n\n"

        await message.answer(
            f"Вы в меню раздела <Факты>.\n\nПоследние факты:\n{text}Выберите действия на кнпоках.",
            keyboard=get_admin_fact_menu()
        )

    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        pass

@labeler.message(payload={"action": "menu_riddles"})
async def admin_riddles_menu(message: Message):
    try:
        user_id = message.from_id
        exists_admin = VkAdminRepository.is_admin(user_id)
        logger.info(f"Получение админа VK {user_id}")

        if not exists_admin:
            logger.info(f"Пользователь {user_id} не является админом")
            await message.answer(
                "⛔ Вы не являетесь администратором. Доступ запрещен"
            )

        riddles_list = await VkRiddleRepository.get_riddle_list()
        text = ""
        if not riddles_list:
            text += "На данный момент загадок нету."
        else:
            for fact in riddles_list:
                text += f"Загадка №{fact.id}\n> Описание: {fact.title}\n> Ссылка: {fact.url}\n\n"

        await message.answer(
            f"Вы в меню раздела <Загадки>.\n\nПоследние загадки:\n{text}Выберите действия на кнпоках.",
            keyboard=get_admin_riddle_menu()
        )

    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        pass

@labeler.message(payload={"action": "menu_opinions"})
async def admin_opinions_menu(message: Message):
    try:
        user_id = message.from_id
        exists_admin = VkAdminRepository.is_admin(user_id)
        logger.info(f"Получение админа VK {user_id}")

        if not exists_admin:
            logger.info(f"Пользователь {user_id} не является админом")
            await message.answer(
                "⛔ Вы не являетесь администратором. Доступ запрещен"
            )

        opinions_list = await VkOpinionRepository.get_opinions_list()
        text = ""
        if not opinions_list:
            text += "На данный момент сборов мнений нету."
        else:
            for fact in opinions_list:
                text += f"Сбор №{fact.id}\n> Описание: {fact.title}\n> Ссылка: {fact.url}\n\n"

        await message.answer(
            f"Вы в меню раздела <Сборы Мнений>.\n\nПоследние сборы:\n{text}Выберите действия на кнпоках.",
            keyboard=get_admin_opinions_menu()
        )

    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        pass

@labeler.message(payload={"action": "menu_tests"})
async def admin_test_menu(message: Message):
    try:
        user_id = message.from_id
        exists_admin = VkAdminRepository.is_admin(user_id)
        logger.info(f"Получение админа VK {user_id}")

        if not exists_admin:
            logger.info(f"Пользователь {user_id} не является админом")
            await message.answer(
                "⛔ Вы не являетесь администратором. Доступ запрещен"
            )

        test_list = await VkTestRepository.get_tests_list()
        text = ""
        if not test_list:
            text += "На данный момент тестов нету."
        else:
            for fact in test_list:
                text += f"Тест №{fact.id}\n> Вопрос: {fact.title}\n> Ответы: {fact.options}\n> Ссылка: {fact.url}\n\n"

        await message.answer(
            f"Вы в меню раздела <Тесты>.\n\nПоследние тесты:\n{text}Выберите действия на кнпоках.",
            keyboard=get_admin_tests_menu()
        )

    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        pass