from datetime import datetime, timedelta

from sqlalchemy import select, func, insert, update

from src.admin.models import CommandLog
from src.db import async_session
from src.max.models import Message, ProblemRequest

ADMIN_IDS = [235995783, 12456095, 8177043133, 588276824, 140167601]

class AdminService:
    @classmethod
    def is_admin(cls, user_id: int):
        return user_id in ADMIN_IDS

    @classmethod
    async def get_commands_stats_admin(cls, days: int = 1):
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        async with async_session() as session:
            result = await session.execute(
                select(CommandLog.command, func.count())
                .where(CommandLog.created_at.between(start_date, end_date))
                .group_by(CommandLog.command)
            )
            return  {cmd: count for cmd, count in result.all()}

    @classmethod
    async def log_command_admin(cls, client_id: int, command: str):
        async with async_session() as session:
            stmt = insert(CommandLog).values(
                client_id=client_id, command=command
            )
            await session.execute(stmt)
            await session.commit()


    @classmethod
    async def get_total_messages_last_days_admin(cls):
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)

        async with async_session() as session:
            result = await session.scalar(
                select(func.count()).select_from(Message)
                .where(Message.created_at.between(start_date, end_date))
            )
            return result or 0

    # problem request
    @classmethod
    async def get_problem_request_list(cls):
        async with async_session() as session:
            query = select(ProblemRequest).order_by(ProblemRequest.created_at.desc())
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def get_unviewed_problem_request(cls, limit: int = 15):
        async with async_session() as session:
            result = await session.execute(
                select(ProblemRequest)
                .order_by(
                    ProblemRequest.viewed.asc()
                )
                .limit(limit)
            )
            return result.scalars().all()

    @classmethod
    async def get_problem_request(cls, client_id: int):
        async with async_session() as session:
            query = select(ProblemRequest).filter_by(client_id=client_id)
            result = await session.execute(query)
            res = result.scalar_one_or_none()
            return res

    @classmethod
    async def get_problem_request_by_id(cls, appointment_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(ProblemRequest).filter_by(id=appointment_id)
            )
            return result.scalar_one_or_none()

    @classmethod
    async def add_problem_request(cls, client_id: int, messages: str):
        async with async_session() as session:
            stmt = insert(ProblemRequest).values(
                client_id=client_id,
                messages=messages,
            )
            await session.execute(stmt)
            await session.commit()


    @classmethod
    async def mark_request_viewed(cls, appointment_id: int):
        async with async_session() as session:
            await session.execute(
                update(ProblemRequest)
                .where(ProblemRequest.id == appointment_id)
                .values(viewed=True)
            )
            await session.commit()
