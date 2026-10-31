from datetime import datetime
from typing import Optional

from sqlalchemy import select, insert, update, func

from src.db import async_session
from src.logger_config import setup_logger
from src.vk_bot.models import VKUser, Question, ContentType

logger = setup_logger('repository', 'vk', 'repository_vk_work.log')

class VkUserRepository:
    @classmethod
    async def get_user(cls, user_id: int):
        async with async_session() as session:
            query = select(VKUser).filter_by(vk_id=user_id)
            logger.debug(f"Получение пользователя VK {user_id}")
            result = await session.execute(query)
            res = result.scalar_one_or_none()
            if res:
                logger.debug(f"Пользователь {user_id} найден")
            else:
                logger.debug(f"Пользователь {user_id} не найден")
            return res

    @classmethod
    async def create_user(cls, user_id: int, first_name: str):
        logger.debug(f"Создание VK пользователя {user_id}-{first_name}")
        async with async_session() as session:
            stmt = insert(VKUser).values(vk_id=user_id, first_name=first_name)
            await session.execute(stmt)
            await session.commit()
            logger.debug(f"VK Пользователь {user_id} успешно создан")


    @classmethod
    async def update_last_fact_date(cls, user_id: int):
        logger.debug(f"Обновления поля 'послдений просмотр факта дня', id = {user_id}")
        async with async_session() as session:
            stmt = update(VKUser).filter_by(vk_id=user_id).values(last_fact_date=datetime.now())
            await session.execute(stmt)
            await session.commit()
            logger.debug(f"VK Пользователь {user_id} успешно создан")

class VkFactRepository:
    @classmethod
    async def get_facts_list(cls, limit: int = 10):
        logger.debug(f"Получение списка фактов")
        async with async_session() as session:
            stmt = select(Question).where(Question.type == ContentType.FACT).order_by(Question.created_at.desc()).limit(limit)
            facts = await session.execute(stmt)
            logger.debug(f"Получен список фактов")
            return facts.scalars().all()

    @classmethod
    async def get_fact_by_id(cls, fact_id: int):
        logger.debug(f"Получение теста по ID {fact_id}")
        async with async_session() as session:
            stmt = select(Question).where(Question.id == fact_id)
            fact = await session.execute(stmt)
            logger.debug(f"Получен тест с ID {fact_id}")
            return fact.scalar_one_or_none()

    @classmethod
    async def get_random_fact(cls):
        logger.debug(f"Получение рандомного факта")
        async with async_session() as session:
            stmt = select(Question).where(Question.type == ContentType.FACT).order_by(func.random()).limit(1)
            fact = await session.execute(stmt)
            logger.debug(f"Получен рандомный факт")
            return fact.scalar_one_or_none()

    @classmethod
    async def create_fact(cls, text: str, video_url: Optional[str] = None):
        async with async_session() as session:
            logger.debug(f"Создание Факта")
            stmt = insert(Question).values(type=ContentType.FACT, title=text, video_url=video_url)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def update_fact(cls, fact_id: int, text: str, video_url: Optional[str] = None):
        async with async_session() as session:
            logger.debug(f"Обновление факта ID {fact_id}")
            stmt = update(Question).filter_by(id=fact_id).values(title=text, video_url=video_url)
            await session.execute(stmt)
            await session.commit()

class VkRiddleRepository:
    @classmethod
    async def get_riddle_list(cls, limit: int = 10):
        logger.debug(f"Получение списка загадок")
        async with async_session() as session:
            stmt = select(Question).where(Question.type == ContentType.RIDDLE).order_by(Question.created_at.desc()).limit(limit)
            riddles = await session.execute(stmt)
            logger.debug(f"Получен список фактов")
            return riddles.scalars().all()

    @classmethod
    async def get_riddle_by_id(cls, riddle_id: int):
        logger.debug(f"Получение загадки по ID {riddle_id}")
        async with async_session() as session:
            stmt = select(Question).where(Question.type == ContentType.RIDDLE, Question.id == riddle_id)
            riddle = await session.execute(stmt)
            logger.debug(f"Получена загадка с ID {riddle_id}")
            return riddle.scalar_one_or_none()

    @classmethod
    async def get_random_riddle(cls):
        logger.debug(f"Получение рандомной загадки")
        async with async_session() as session:
            stmt = select(Question).where(Question.type == ContentType.RIDDLE).order_by(func.random()).limit(1)
            riddle = await session.execute(stmt)
            logger.debug(f"Получена рандомная загадка")
            return riddle.scalar_one_or_none()

    @classmethod
    async def create_riddle(cls, text: str, video_url: Optional[str] = None):
        async with async_session() as session:
            logger.debug(f"Создание загадки")
            stmt = insert(Question).values(type=ContentType.RIDDLE, title=text, video_url=video_url)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def update_riddle(cls, riddle_id: int, text: str, video_url: Optional[str] = None):
        async with async_session() as session:
            logger.debug(f"Обновление задачи по ID {riddle_id}")
            stmt = update(Question).filter_by(id=riddle_id).values(title=text, video_url=video_url)
            await session.execute(stmt)
            await session.commit()


class VkOpinionRepository:
    @classmethod
    async def get_opinions_list(cls, limit: int = 10):
        logger.debug(f"Получение списка сборов")
        async with async_session() as session:
            stmt = select(Question).where(Question.type == ContentType.OPINION).order_by(Question.created_at.desc()).limit(limit)
            opinions = await session.execute(stmt)
            logger.debug(f"Получен список сборов")
            return opinions.scalars().all()

    @classmethod
    async def get_opinion_by_id(cls, op_id: int):
        logger.debug(f"Получение сбора ID {op_id}")
        async with async_session() as session:
            stmt = select(Question).where(Question.id == op_id)
            opinion = await session.execute(stmt)
            logger.debug(f"Получен сбор по ID {op_id}")
            return opinion.scalar_one_or_none()

    @classmethod
    async def get_random_opinion(cls):
        logger.debug(f"Получение рандомного сбора")
        async with async_session() as session:
            stmt = select(Question).where(Question.type == ContentType.OPINION).order_by(func.random()).limit(1)
            opinion = await session.execute(stmt)
            logger.debug(f"Получен рандомный сбор")
            return opinion.scalar_one_or_none()

    @classmethod
    async def create_opinion(cls, text: str, video_url: Optional[str] = None):
        async with async_session() as session:
            logger.debug(f"Создание сбора мнений")
            stmt = insert(Question).values(type=ContentType.OPINION, title=text, video_url=video_url)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def update_opinion(cls, opinion_id: int, text: str, video_url: Optional[str] = None):
        async with async_session() as session:
            logger.debug(f"Обновление факта ID {opinion_id}")
            stmt = update(Question).filter_by(id=opinion_id).values(title=text, video_url=video_url)
            await session.execute(stmt)
            await session.commit()

class VkTestRepository:
    @classmethod
    async def get_tests_list(cls, limit: int = 10):
        logger.debug(f"Получение списка тестов")
        async with async_session() as session:
            stmt = select(Question).where(Question.type == ContentType.TEST).order_by(Question.created_at.desc()).limit(limit)
            tests = await session.execute(stmt)
            logger.debug(f"Получен список тестов")
            return tests.scalars().all()

    @classmethod
    async def get_test_by_id(cls, test_id: int):
        logger.debug(f"Получение теста ID {test_id}")
        async with async_session() as session:
            stmt = select(Question).where(Question.type == ContentType.TEST, Question.id == test_id)
            riddle = await session.execute(stmt)
            logger.debug(f"Получен тест с ID {test_id}")
            return riddle.scalar_one_or_none()

    @classmethod
    async def get_random_test(cls):
        logger.debug(f"Получение рандомного теста")
        async with async_session() as session:
            stmt = select(Question).where(Question.type == ContentType.TEST).order_by(func.random()).limit(1)
            test = await session.execute(stmt)
            logger.debug(f"Получен рандомный тест")
            return test.scalar_one_or_none()

    @classmethod
    async def create_test(cls, title: str, video_url: Optional[str] = None):
        async with async_session() as session:
            logger.debug(f"Создание теста")
            stmt = insert(Question).values(type=ContentType.TEST, title=title, video_url=video_url)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def update_test(cls, test_id: int, text: str, video_url: Optional[str] = None):
        async with async_session() as session:
            logger.debug(f"Обновление теста по ID {test_id}")
            stmt = update(Question).filter_by(id=test_id).values(title=text, video_url=video_url)
            await session.execute(stmt)
            await session.commit()
