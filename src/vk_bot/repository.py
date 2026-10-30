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

class VkOpinionRepository:
    @classmethod
    async def get_random_opinion(cls):
        logger.debug(f"Получение рандомного сбора")
        async with async_session() as session:
            stmt = select(Question).where(Question.type == ContentType.OPINION).order_by(func.random()).limit(1)
            fact = await session.execute(stmt)
            logger.debug(f"Получен рандомный сбор")
            return fact.scalar_one_or_none()

    @classmethod
    async def create_opinion(cls, text: str, video_url: Optional[str] = None):
        async with async_session() as session:
            logger.debug(f"Создание сбора мнений")
            stmt = insert(Question).values(type=ContentType.OPINION, title=text, video_url=video_url)
            await session.execute(stmt)
            await session.commit()