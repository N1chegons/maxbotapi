from sqlalchemy import select, update, insert

from src.config import settings
from src.db import async_session
from src.max.models import Session, Message, Request, Feedback

FOLDER_ID = settings.YC_FOLDER_ID
API_KEY = settings.YC_API_SPEECHKIT

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
            query = select(Request).filter_by(client_id=client_id)
            result = await session.execute(query)
            res = result.scalar_one_or_none()
            return res

    @classmethod
    async def add_request(cls, client_id: int, contact: str, messages: str):
        async with async_session() as session:
            stmt = insert(Request).values(
                client_id=client_id,
                contact=contact,
                messages=messages,
            )
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def get_last_messages(cls, client_id: int, limit: int = 20) -> list:
        async with async_session() as session:
            stmt = (
                select(Message)
                .filter_by(client_id=client_id)
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

class AudioService:
    @classmethod
    def recognize_from_s3(cls, filelink: str, api_key: str) -> str:
        import requests, time
        POST = 'https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize'
        body = {
            "config": {
                "specification": {
                    "languageCode": "ru-RU",
                    "audioEncoding": "MP3"  # ← ключевое изменение
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
        return ' '.join(texts)