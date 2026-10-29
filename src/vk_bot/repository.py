from sqlalchemy import select, insert

from src.db import async_session
from src.logger_config import setup_logger
from src.vk_bot.models import VKUser

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
        logger.info(f"Создание VK пользователя {user_id}-{first_name}")
        async with async_session() as session:
            stmt = insert(VKUser).values(vk_id=user_id, first_name=first_name)
            await session.execute(stmt)
            await session.commit()
            logger.info(f"VK Пользователь {user_id} успешно создан")