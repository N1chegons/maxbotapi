# from datetime import datetime
#
# from sqlalchemy import select, func
#
# from src.db import async_session
# from src.max.models import Session, Request, Mark
#
# class StaticService:
#     @classmethod
#     async def get_session_static_count(cls, start_date: datetime, end_date: datetime):
#         async with async_session() as session:
#             sessions_count = await session.scalar(
#                 select(func.count()).select_from(Session).where(
#                     Session.created_at.between(start_date, end_date)
#                 )
#             )
#             return sessions_count or 0
#
#     @classmethod
#     async def get_session_static_by_topic(cls, start_date: datetime, end_date: datetime):
#         async with async_session() as session:
#             result = await session.execute(
#                 select(Session.topic, func.count())
#                 .where(Session.created_at.between(start_date, end_date))
#                 .group_by(Session.topic)
#             )
#
#             return {row[0]: row[1] for row in result.all()}
#
#
#     @classmethod
#     async def get_marks_static(cls, start_date: datetime, end_date: datetime):
#         async with async_session() as session:
#             marks_result = await session.execute(
#                 select(Mark).where(
#                     Mark.created_at.between(start_date, end_date)
#                 ).order_by(Mark.created_at.desc())
#             )
#
#             return marks_result.scalars().all()
#
#     @classmethod
#     async def get_request_static(cls, start_date: datetime, end_date: datetime):
#         async with async_session() as session:
#             requests_result = await session.execute(
#                 select(Request).where(
#                     Request.created_at.between(start_date, end_date)
#                 ).order_by(Request.created_at.desc())
#             )
#
#             return requests_result.scalars().all()
#
