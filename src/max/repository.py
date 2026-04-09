import aiohttp
from sqlalchemy import select, update, insert

from src.config import settings
from src.db import async_session
from src.max.models import Session, Message, Request, Mark


class MaxService:
    # session section
    @classmethod
    async def get_session(cls, user_id: int):
        async with async_session() as session:
            query = select(Session).filter_by(client_id=user_id)
            result = await session.execute(query)
            res = result.scalar_one_or_none()
            return res

    @classmethod
    async def update_session(cls, user_id: int, topic: str):
        async with async_session() as session:
            stmt = (
                update(Session)
                .filter_by(client_id=user_id)
                .values(topic=topic)
            )
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def create_session(cls, user_id: int, topic: str):
        async with async_session() as session:
            already_user = await cls.get_session(user_id)
            if already_user is not None:
                await cls.update_session(user_id, topic)
            else:
                stmt = insert(Session).values(client_id=user_id, topic=topic)
                add_new_session = await session.execute(stmt)
                await session.commit()

    # history message section
    @classmethod
    async def add_message(cls, user_id: int, role: str, content: str):
        async with async_session() as session:
            stmt = insert(Message).values(
                client_id=user_id,
                role=role,
                content=content
            )
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def get_history(cls, user_id: int, limit: int = 10):
        async with async_session() as session:
            stmt = (
                select(Message)
                .filter_by(client_id=user_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()
            return [
                {"role": m.role, "content": m.content}
                for m in reversed(messages)
            ]

    #consult request
    @classmethod
    async def get_request(cls, client_id: int):
        async with async_session() as session:
            query = select(Session).filter_by(client_id=client_id)
            result = await session.execute(query)
            res = result.scalar_one_or_none()
            return res

    @classmethod
    async def add_request(cls, client_id: int, username: str):
        async with async_session() as session:
            stmt = insert(Request).values(
                client_id=client_id,
                contact=username
            )
            await session.execute(stmt)
            await session.commit()

    #mark section
    @classmethod
    async def add_mark(cls, client_id: int, fragment: str, session_topic: str = None, next_topic: str = None):
        async with async_session() as session:
            stmt = insert(Mark).values(
                client_id=client_id,
                fragment=fragment,
                session_topic=session_topic,
                next_topic=next_topic
            )
            await session.execute(stmt)
            await session.commit()

class AudioService:
    ...