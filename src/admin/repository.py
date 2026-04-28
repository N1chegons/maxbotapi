from datetime import datetime, timedelta

from sqlalchemy import select, func, insert

from src.admin.models import CommandLog
from src.db import async_session

ADMIN_IDS = [235995783, 12456095]

# class AdminService:
#     @classmethod
#     def is_admin(cls, user_id: int):
#         return user_id in ADMIN_IDS
#
#     @classmethod
#     async def get_commands_stats_admin(cls, days: int = 1):
#         end_date = datetime.utcnow()
#         start_date = end_date - timedelta(days=days)
#
#         async with async_session() as session:
#             result = await session.execute(
#                 select(CommandLog.command, func.count())
#                 .where(CommandLog.created_at.between(start_date, end_date))
#                 .group_by(CommandLog.command)
#             )
#             return  {cmd: count for cmd, count in result.all()}
#
#     @classmethod
#     async def log_command_admin(cls, client_id: int, command: str):
#         async with async_session() as session:
#             stmt = insert(CommandLog).values(
#                 client_id=client_id, command=command
#             )
#             await session.execute(stmt)
#             await session.commit()
#
#     @classmethod
#     async def get_last_feedbacks_admin(cls, flag: bool):
#         async with async_session() as session:
#             query = select(Feedback).filter_by(is_positive=flag).order_by(Feedback.created_at.desc()).limit(5)
#             result = await session.execute(query)
#             return result.scalars().all()
#
#     @classmethod
#     async def get_total_messages_last_days_admin(cls):
#         end_date = datetime.utcnow()
#         start_date = end_date - timedelta(days=1)
#
#         async with async_session() as session:
#             result = await session.scalar(
#                 select(func.count()).select_from(Message)
#                 .where(Message.created_at.between(start_date, end_date))
#             )
#             return result or 0
#
#     @classmethod
#     async def get_appointments_admin(cls):
#         pass
