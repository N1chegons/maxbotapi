from datetime import datetime, timedelta

from sqlalchemy import select, update, insert, delete, or_

from src.config import settings
from src.db import async_session
from src.max.models import Session, Message, Request, User, UserState, SubsStatus, SubsTier, MemoryMode

FOLDER_ID = settings.YC_FOLDER_ID
API_KEY = settings.YC_API_SPEECHKIT


# noinspection PyDeprecation
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
            stmt = insert(User).values(user_id=user_id, platform=platform)
            await session.execute(stmt)
            await session.commit()

    # user state
    @classmethod
    async def update_user_state(cls, user_id: int, new_state: UserState):
        async with async_session() as session:
            await session.execute(
                update(User).filter_by(user_id=user_id).values(state=new_state)
            )
            await session.commit()

    # memory modes
    @classmethod
    async def update_memory_mode(cls, user_id: int, new_mode: MemoryMode):
        async with async_session() as session:
            await session.execute(
                update(User).filter_by(user_id=user_id).values(memory_mode=new_mode)
            )
            await session.commit()

    @classmethod
    async def update_is_memory_setup_completed(cls, user_id: int):
        async with async_session() as session:
            await session.execute(
                update(User).filter_by(user_id=user_id).values(is_memory_setup_completed=True)
            )
            await session.commit()

    # session section
    @classmethod
    async def get_session(cls, user_id: int):
        async with async_session() as session:
            query = select(Session).filter_by(user_id=user_id).order_by(Session.started_at.desc()).limit(1)
            result = await session.execute(query)
            res = result.scalar_one_or_none()
            return res

    @classmethod
    async def create_session(cls, user_id: int):
        async with async_session() as session:
            stmt = insert(Session).values(user_id=user_id)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def delete_session(cls, user_id: int):
        async with async_session() as session:
            await cls.delete_messages(user_id)

            stmt = delete(Session).filter_by(user_id=user_id)
            await session.execute(stmt)
            await session.commit()

    # history message section
    @classmethod
    async def add_message(cls, user_id: int, session_id: int, role: str, content: str):
        async with async_session() as session:
            stmt = insert(Message).values(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content
            )
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def get_history(cls, user_id: int, limit: int = 200):
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
    async def delete_messages(cls, user_id: int):
        async with async_session() as session:
            await session.execute(
                delete(Message).filter_by(user_id=user_id)
            )
            await session.commit()

    #consult request
    @classmethod
    async def get_unviewed_request(cls, limit: int = 15):
        async with async_session() as session:
            result = await session.execute(
                select(Request)
                .order_by(
                    Request.viewed.asc(),
                    Request.appointment_date.asc()
                )
                .limit(limit)
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
    async def start_trial(cls, user_id: int):
        async with async_session() as session:
            now = datetime.utcnow()
            await session.execute(
                update(User)
                .filter_by(user_id=user_id)
                .values(
                    trial_started_at=now,
                    trial_ends_at=now + timedelta(days=14),
                    state=UserState.TRIAL_ACTIVE
                )
            )
            await session.commit()

    @classmethod
    async def expire_trial_if_needed(cls, user_id: int):
        user = await cls.get_user(user_id)

        if user.state != UserState.TRIAL_ACTIVE:
            return

        if user.trial_ends_at and user.trial_ends_at <= datetime.utcnow():
            async with async_session() as session:
                await session.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(
                        state=UserState.TRIAL_ENDED_NOT_PAID,
                        subscription_status=SubsStatus.expired
                    )
                )
                await session.commit()

    @classmethod
    async def activate_subscription(cls, user_id: int, tier: SubsTier, state: UserState):
        async with async_session() as session:
            await session.execute(
                update(User)
                .filter_by(user_id=user_id)
                .values(
                    subscription_tier=tier,
                    subscription_ends_at=datetime.utcnow() + timedelta(days=30),
                    state=state
                )
            )
            await session.commit()

    @classmethod
    async def change_subscription_status(cls, user_id: int, status: SubsStatus):
        async with async_session() as session:
            await session.execute(
                update(User)
                .filter_by(user_id=user_id)
                .values(
                    subscription_status=status,
                )
            )
            await session.commit()

    @classmethod
    async def save_payment_method(cls, user_id: int, payment_method_id: str):
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(payment_method_id=payment_method_id)
            )
            await session.commit()

    @classmethod
    async def update_subscription_end_date(cls, user_id: int, new_end_date: datetime):
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(subscription_ends_at=new_end_date)
            )
            await session.commit()

    @classmethod
    async def mark_started_subscription(cls, user_id: int):
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(has_started_subscription=True)
            )
            await session.commit()

    @classmethod
    async def can_send_message(cls, user_id: int) -> bool:
        # Сначала обновляем статус триала
        await cls.expire_trial_if_needed(user_id)

        user = await cls.get_user(user_id)
        if not user:
            return False

        now = datetime.utcnow()

        if user.subscription_status == SubsStatus.active:
            return user.subscription_ends_at and user.subscription_ends_at > now

        if user.subscription_status == SubsStatus.grace_period:
            return user.subscription_ends_at and user.subscription_ends_at > now

        if user.subscription_status == SubsStatus.cancelled:
            return user.subscription_ends_at and user.subscription_ends_at > now

        if user.subscription_status == SubsStatus.trial:
            return user.trial_ends_at and user.trial_ends_at > now

        return False

    # -------------------------------------- CRON ---------------------------------------
    @classmethod
    async def get_users_for_auto_charge(cls):
        async with async_session() as session:
            now = datetime.utcnow()
            three_days_ago = now - timedelta(days=3)

            result = await session.execute(
                select(User)
                .where(
                    User.subscription_status.in_([SubsStatus.active, SubsStatus.grace_period]),
                    User.payment_method_id.isnot(None),
                    User.subscription_ends_at <= now,
                    or_(
                        User.subscription_status == SubsStatus.grace_period,
                        User.subscription_ends_at >= three_days_ago
                    )
                )
            )
            return result.scalars().all()

    @classmethod
    async def get_users_with_expired_trial(cls):
        async with async_session() as session:
            now = datetime.utcnow()  # ← naive
            result = await session.execute(
                select(User)
                .where(
                    User.subscription_status == SubsStatus.trial,
                    User.trial_ends_at <= now
                )
            )
            return result.scalars().all()

    @classmethod
    async def update_grace_period_attempts(cls, user_id: int, attempts: int):
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(grace_period_attempts=attempts)
            )
            await session.commit()

    @classmethod
    async def activate_subscription_after_trial(cls, user_id: int):
        async with async_session() as session:
            new_end = datetime.utcnow() + timedelta(days=31)  # ← naive
            await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(
                    subscription_status=SubsStatus.active,
                    subscription_ends_at=new_end,
                    trial_ends_at=None,
                    has_started_subscription=True,
                    state=UserState.PAID,
                    grace_period_attempts=0
                )
            )
            await session.commit()

class AudioService:
    @classmethod
    def recognize_from_s3(cls, filelink: str, api_key: str) -> str:
        import requests, time
        # noinspection PyPep8Naming
        POST = 'https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize'
        body = {
            "config": {
                "specification": {
                    "languageCode": "ru-RU"
                }
            },
            "audio": {
                "uri": filelink
            }
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
