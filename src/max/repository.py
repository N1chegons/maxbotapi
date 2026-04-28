import os
from datetime import datetime

from maxapi.types import InputMedia
from sqlalchemy import select, update, insert, delete

from src.config import settings
from src.db import async_session
from src.max.models import Session, Message, Request, Feedback, User, UserState

FOLDER_ID = settings.YC_FOLDER_ID
API_KEY = settings.YC_API_SPEECHKIT

class MaxService:
    # user section
    @classmethod
    async def get_user(cls, user_id: int):
        async with async_session() as session:
            query = select(User).filter_by(user_id=user_id)
            result = await session.execute(query)
            res = result.scalar_one_or_none()
            return res

    @classmethod
    async def create_user(cls, user_id: int, platform: str):
        async with async_session() as session:
            stmt = insert(User).values(user_id=user_id)
            add_new_session = await session.execute(stmt)
            await session.commit()

    # session section
    @classmethod
    async def get_session(cls, user_id: int):
        async with async_session() as session:
            query = select(Session).filter_by(user_id=user_id)
            result = await session.execute(query)
            res = result.scalar_one_or_none()
            return res

    @classmethod
    async def create_session(cls, user_id: int):
        async with async_session() as session:
            stmt = insert(Session).values(user_id=user_id)
            add_new_session = await session.execute(stmt)
            await session.commit()

    # history message section
    @classmethod
    async def add_message(cls, user_id: int, role: str, content: str):
        async with async_session() as session:
            stmt = insert(Message).values(
                user_id=user_id,
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
                .filter_by(user_id=user_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()
            return [
                {"role": m.role, "content": m.content}
                for m in reversed(messages)
            ]

    @classmethod
    async def delete_non_today_messages(cls):
        from datetime import datetime, timezone

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        async with async_session() as session:
            result = await session.execute(
                delete(Message).where(Message.created_at < today_start)
            )
            await session.commit()
            print(f"[CLEANUP] Удалено {result.rowcount} сообщений")

    #consult request
    @classmethod
    async def get_request_list(cls):
        async with async_session() as session:
            query = select(Request).order_by(Request.created_at.desc())
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def get_unviewed_request(cls):
        async with async_session() as session:
            result = await session.execute(
                select(Request)
                .where(Request.viewed == False)
                .order_by(Request.appointment_date.asc())
            )
            return result.scalars().all()

    @classmethod
    async def get_request(cls, client_id: int):
        async with async_session() as session:
            query = select(Request).filter_by(client_id=client_id)
            result = await session.execute(query)
            res = result.scalar_one_or_none()
            return res

    @classmethod
    async def get_request_by_id(cls, appointment_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(Request).filter_by(id=appointment_id)
            )
            return result.scalar_one_or_none()

    @classmethod
    async def add_request(cls, client_id: int, contact: str, messages: str, appointment_date: datetime):
        async with async_session() as session:
            stmt = insert(Request).values(
                client_id=client_id,
                contact=contact,
                messages=messages,
                appointment_date=appointment_date
            )
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def mark_request_viewed(cls, appointment_id: int):
        async with async_session() as session:
            await session.execute(
                update(Request)
                .where(Request.id == appointment_id)
                .values(viewed=True)
            )
            await session.commit()

    @classmethod
    async def get_last_messages(cls, client_id: int, limit: int = 20) -> list:
        async with async_session() as session:
            stmt = (
                select(Message)
                .filter_by(user_id=client_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()
            return list(reversed(messages))

    #mark section
    @classmethod
    async def add_feedback(cls, client_id: int, fragment: str, is_positive: bool = True, session_topic: str = None,
                           next_topic: str = None):
        async with async_session() as session:
            stmt = insert(Feedback).values(
                client_id=client_id,
                fragment=fragment,
                is_positive=is_positive,
                next_topic=next_topic,
                session_topic = session_topic
            )
            await session.execute(stmt)
            await session.commit()

    # utils
    @classmethod
    async def get_next_free_date(cls) -> datetime:
        import pytz
        from datetime import datetime, timedelta

        msk = pytz.timezone('Europe/Moscow')
        now_msk = datetime.now(msk)

        date_msk = (now_msk + timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)

        date_utc = date_msk.astimezone(pytz.UTC).replace(tzinfo=None)

        async with async_session() as session:
            while True:
                result = await session.execute(
                    select(Request).where(Request.appointment_date == date_utc)
                )
                if result.scalar_one_or_none() is None:
                    return date_utc

                date_msk += timedelta(days=1)
                date_utc = date_msk.astimezone(pytz.UTC).replace(tzinfo=None)

    @classmethod
    async def check_and_update_trial_status(cls, user_id: int) -> str:
        async with async_session() as session:
            # Получаем пользователя
            user = await cls.get_user(user_id)

            # Если не в триале — возвращаем его статус
            if user.state != UserState.TRIAL_ACTIVE:
                return user.state

            # Если триал ещё не закончился
            if user.trial_ends_at and user.trial_ends_at > datetime.utcnow():
                return UserState.TRIAL_ACTIVE

            # Триал закончился — обновляем
            stmt = update(User).filter_by(user_id=user_id).values(
                state=UserState.TRIAL_ENDED_NOT_PAID
            )
            await session.execute(stmt)
            await session.commit()

            return UserState.TRIAL_ENDED_NOT_PAID

    @classmethod
    async def can_send_message(cls, user_id: int) -> bool:
        """Может ли пользователь отправлять новые сообщения"""
        state = await cls.check_and_update_trial_status(user_id)

        # Запрещённые статусы (здесь НЕЛЬЗЯ писать)
        forbidden_states = [UserState.TRIAL_ENDED_NOT_PAID]

        # Можно писать, если статус НЕ в запрещённых
        return state not in forbidden_states

class AudioService:
    @classmethod
    def recognize_from_s3(cls, filelink: str, api_key: str) -> str:
        import requests, time
        POST = 'https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize'
        body = {
            "config": {
                "specification": {
                    "languageCode": "ru-RU",
                    "audioEncoding": "MP3"
                }
            },
            "audio": {"uri": filelink}
        }
        headers = {'Authorization': f'Api-Key {api_key}'}

        resp = requests.post(POST, headers=headers, json=body)
        if resp.status_code != 200:
            raise Exception(f"Ошибка старта: {resp.status_code} - {resp.text}")

        data = resp.json()
        operation_id = data['id']

        while True:
            time.sleep(5)
            resp = requests.get(f'https://operation.api.cloud.yandex.net/operations/{operation_id}', headers=headers)
            data = resp.json()
            if data.get('done'):
                break

        texts = [chunk['alternatives'][0]['text'] for chunk in data['response']['chunks']]
        return ' '.join(texts),



class VideoService:
    def __init__(self):
        self.cache_dir = "video_cache"
        self.video_files = {
            "consultation": "04.mp4",
            "about_bot": "02.mp4",
            "about_expert": "01.mp4"
        }
        self.video_media_cache = {}

    async def preload_videos(self):
        for key, file_name in self.video_files.items():
            file_path = os.path.join(self.cache_dir, file_name)
            if os.path.exists(file_path):
                self.video_media_cache[key] = InputMedia(path=file_path)