from datetime import datetime, timedelta

from sqlalchemy import select, update, insert, delete, or_

from src.admin.repository import AdminService
from src.config import settings
from src.db import async_session
from src.logger_config import setup_logger
from src.max.models import Session, Message, Request, User, UserState, SubsStatus, SubsTier, MemoryMode

logger = setup_logger('repository', 'max', 'repository_work.log')

FOLDER_ID = settings.YC_FOLDER_ID
API_KEY = settings.YC_API_SPEECHKIT


# noinspection PyDeprecation
class MaxService:
    # user section
    @classmethod
    async def get_user(cls, user_id: int):
        logger.debug(f"Получение пользователя {user_id}")
        async with async_session() as session:
            query = select(User).filter_by(user_id=user_id)
            result = await session.execute(query)
            res = result.scalar_one_or_none()
            if res:
                logger.debug(f"Пользователь {user_id} найден")
            else:
                logger.debug(f"Пользователь {user_id} не найден")
            return res

    @classmethod
    async def get_all_users(cls):
        async with async_session() as session:
            query = select(User)
            result = await session.execute(query)
            return result.scalars().all()

    @classmethod
    async def create_user(cls, user_id: int, platform: str):
        logger.info(f"Создание пользователя {user_id} на платформе {platform}")
        async with async_session() as session:
            stmt = insert(User).values(user_id=user_id, platform=platform)
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Пользователь {user_id} успешно создан")

    @classmethod
    async def get_users_silent_between(cls, min_minutes: int, max_minutes: int, bot_name: str = None):
        async with async_session() as session:
            max_ago = datetime.utcnow() - timedelta(minutes=min_minutes)
            min_ago = datetime.utcnow() - timedelta(minutes=max_minutes)

            query = select(User).where(
                User.memory_mode != MemoryMode.none
            )

            if bot_name == "MAX_Dominant":
                query = query.where(
                    User.last_message_at_dominator <= max_ago,
                    User.last_message_at_dominator >= min_ago,
                    User.last_message_at_dominator.isnot(None)
                )
            else:
                query = query.where(
                    User.last_message_at <= max_ago,
                    User.last_message_at >= min_ago,
                    User.last_message_at.isnot(None)
                )

            result = await session.execute(query)
            return result.scalars().all()

    # user state
    @classmethod
    async def update_user_state(cls, user_id: int, new_state: UserState):
        logger.debug(f"Обновление состояния пользователя {user_id} на {new_state}")
        async with async_session() as session:
            await session.execute(
                update(User).filter_by(user_id=user_id).values(state=new_state)
            )
            await session.commit()
            logger.debug(f"Состояние пользователя {user_id} обновлено на {new_state}")

    # memory modes
    @classmethod
    async def update_memory_mode(cls, user_id: int, new_mode: MemoryMode):
        logger.info(f"Пользователь {user_id} изменил режим памяти на {new_mode}")
        async with async_session() as session:
            await session.execute(
                update(User).filter_by(user_id=user_id).values(memory_mode=new_mode)
            )
            await session.commit()

    @classmethod
    async def update_is_memory_setup_completed(cls, user_id: int):
        logger.debug(f"Отметка о завершении настройки памяти для пользователя {user_id}")
        async with async_session() as session:
            await session.execute(
                update(User).filter_by(user_id=user_id).values(is_memory_setup_completed=True)
            )
            await session.commit()

    # session section
    @classmethod
    async def get_session(cls, user_id: int):
        logger.debug(f"Получение активной сессии для пользователя {user_id}")
        async with async_session() as session:
            query = select(Session).filter_by(user_id=user_id).order_by(Session.started_at.desc()).limit(1)
            result = await session.execute(query)
            res = result.scalar_one_or_none()
            if res:
                logger.debug(f"Найдена сессия {res.id} для пользователя {user_id}")
            return res

    @classmethod
    async def create_session(cls, user_id: int):
        logger.info(f"Создание новой сессии для пользователя {user_id}")
        async with async_session() as session:
            stmt = insert(Session).values(user_id=user_id)
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Сессия для пользователя {user_id} создана")

    @classmethod
    async def delete_session(cls, user_id: int):
        logger.warning(f"Удаление сессии пользователя {user_id}")
        async with async_session() as session:
            await cls.delete_messages(user_id)

            stmt = delete(Session).filter_by(user_id=user_id)
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Сессия пользователя {user_id} удалена")

    # history message section
    @classmethod
    async def add_message(cls, user_id: int, session_id: int, role: str, content: str, bot_name: str):
        logger.debug(f"Добавление сообщения от {role} для пользователя {user_id} в сессию {session_id}")
        async with async_session() as session:
            stmt = insert(Message).values(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content,
                bot_name=bot_name,
            )
            await session.execute(stmt)
            logger.debug(f"Сообщение для пользователя {user_id} добавлено")

            if role == "user":
                update_values = {}

                if bot_name == "MAX_Dominant":
                    update_values["message_count_dominator"] = User.message_count_dominator + 1
                    update_values["last_message_at_dominator"] = datetime.utcnow()
                else:
                    update_values["message_count"] = User.message_count + 1
                    update_values["last_message_at"] = datetime.utcnow()

                await session.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(**update_values)
                )

            await session.commit()
            logger.debug(f"Последнее сообщение для пользователя {user_id} обновлено")

    @classmethod
    async def get_history(cls, user_id: int, bot_name: str, limit: int = 200):
        async with async_session() as session:
            stmt = (
                select(Message)
                .where(
                    Message.user_id == user_id,
                    Message.bot_name == bot_name
                )
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
    async def get_last_bot_for_user(cls, user_id: int) -> str | None:
        async with async_session() as session:
            result = await session.execute(
                select(Message.bot_name)
                .where(Message.user_id == user_id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            return row

    @classmethod
    async def delete_messages(cls, user_id: int):
        logger.info(f"Удаление всех сообщений пользователя {user_id}")
        async with async_session() as session:
            await session.execute(
                delete(Message).filter_by(user_id=user_id)
            )
            await session.commit()
            logger.info(f"Сообщения пользователя {user_id} удалены")

    #consult request
    @classmethod
    async def get_unviewed_request(cls, limit: int = 15):
        logger.debug(f"Получение непросмотренных заявок (лимит {limit})")
        async with async_session() as session:
            result = await session.execute(
                select(Request)
                .order_by(
                    Request.viewed.asc(),
                    Request.appointment_date.asc()
                )
                .limit(limit)
            )
            requests = result.scalars().all()
            logger.debug(f"Найдено {len(requests)} непросмотренных заявок")
            return requests

    @classmethod
    async def get_request(cls, client_id: int):
        logger.debug(f"Получение заявки для клиента {client_id}")
        async with async_session() as session:
            query = select(Request).filter_by(client_id=client_id)
            result = await session.execute(query)
            res = result.scalars().first()
            return res

    @classmethod
    async def get_request_by_id(cls, appointment_id: int):
        logger.debug(f"Получение заявки по ID {appointment_id}")
        async with async_session() as session:
            result = await session.execute(
                select(Request).filter_by(id=appointment_id)
            )
            return result.scalar_one_or_none()

    @classmethod
    async def add_request(cls, client_id: int, contact: str, messages: str, appointment_date: datetime):
        logger.info(f"Добавление заявки для пользователя {client_id}")

        async with async_session() as session:
            result = await session.execute(
                select(Request)
                .where(
                    Request.client_id == client_id,
                    Request.created_at > datetime.utcnow() - timedelta(seconds=5)
                )
                .limit(1)
            )
            if result.scalar_one_or_none():
                logger.warning(f"⚠️ Дубль записи для {client_id}, пропускаем")
                return False

            result = await session.execute(
                select(Request)
                .where(
                    Request.client_id == client_id,
                    Request.created_at > datetime.utcnow() - timedelta(hours=24)
                )
                .limit(1)
            )

            if result.scalar_one_or_none():
                last = result.scalar_one_or_none()
                seconds_left = (last.created_at + timedelta(hours=24) - datetime.utcnow()).total_seconds()
                hours_left = int(seconds_left // 3600)
                minutes_left = int((seconds_left % 3600) // 60)
                logger.warning(f"⚠️ Повторная запись для {client_id} через {hours_left}ч {minutes_left}м")
                return False, f"⏳ Повторная запись доступна через {hours_left}ч {minutes_left}м"

            stmt = insert(Request).values(
                client_id=client_id,
                contact=contact,
                messages=messages,
                appointment_date=appointment_date
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(f"✅ Заявка для пользователя {client_id} добавлена")
            return True

    @classmethod
    async def mark_request_viewed(cls, appointment_id: int):
        logger.debug(f"Отметка заявки {appointment_id} как просмотренной")
        async with async_session() as session:
            await session.execute(
                update(Request)
                .where(Request.id == appointment_id)
                .values(viewed=True)
            )
            await session.commit()

    @classmethod
    async def has_active_request(cls, user_id: int, request_type: str = "consultation"):
        async with async_session() as session:
            query = select(Request).where(Request.client_id == user_id)

            if request_type == "consultation":
                query = query.where(
                    Request.appointment_date.isnot(None),
                    Request.viewed == False
                )
            else:
                query = query.where(
                    Request.appointment_date.is_(None),
                    Request.viewed == False
                )

            result = await session.execute(query.order_by(Request.created_at.desc()).limit(1))
            return result.scalar_one_or_none() is not None

    @classmethod
    async def get_last_messages(cls, client_id: int, limit: int = 20) -> list:
        logger.debug(f"Получение последних {limit} сообщений для клиента {client_id}")
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

    @classmethod
    async def get_last_messages_for_dominant(cls, client_id: int, limit: int = 20) -> list:
        logger.debug(f"Получение последних {limit} сообщений для клиента {client_id} с бота Dominant")
        async with async_session() as session:
            stmt = (
                select(Message)
                .filter_by(user_id=client_id, bot_name="MAX_Dominant")
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
    async def activate_subscription(cls, user_id: int, tier: SubsTier, state: UserState):
        logger.info(f"Активация подписки {tier} для пользователя {user_id}")
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
            logger.info(f"Подписка для пользователя {user_id} активирована до {datetime.utcnow() + timedelta(days=30)}")

    @classmethod
    async def change_subscription_status(cls, user_id: int, status: SubsStatus):
        logger.warning(f"Изменение статуса подписки пользователя {user_id} на {status}")
        async with async_session() as session:
            await session.execute(
                update(User)
                .filter_by(user_id=user_id)
                .values(
                    subscription_status=status,
                )
            )
            await session.commit()
            logger.info(f"Статус подписки пользователя {user_id} изменён на {status}")

    @classmethod
    async def save_payment_method(cls, user_id: int, payment_method_id: str):
        logger.info(f"Сохранение метода оплаты для пользователя {user_id}")
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(payment_method_id=payment_method_id)
            )
            await session.commit()
            logger.info(f"Метод оплаты для пользователя {user_id} сохранён")

    @classmethod
    async def update_subscription_end_date(cls, user_id: int, new_end_date: datetime):
        logger.info(f"Обновление даты окончания подписки пользователя {user_id} на {new_end_date}")
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(subscription_ends_at=new_end_date)
            )
            await session.commit()

    @classmethod
    async def can_send_message(cls, user_id: int, bot_name: str = "MAX_Empathetic") -> bool:
        logger.debug(f"Проверка возможности отправки сообщения для пользователя {user_id} в боте {bot_name}")

        user = await cls.get_user(user_id)
        if not user:
            logger.debug(f"Пользователь {user_id} не найден")
            return False

        now = datetime.utcnow()

        if bot_name == "MAX_Dominant":
            message_count = user.message_count_dominator
            free_limit = user.free_messages_limit_for_dominant
            subscription_status = user.subscription_status_dominator
            subscription_ends_at = user.subscription_ends_at_dominator

            if user.trial_dominator_ends_at and user.trial_dominator_ends_at > now:
                trial_messages_left = user.messages_count_trial_dominator
                if trial_messages_left > 0:
                    logger.debug(
                        f"Пользователь {user_id} может отправить сообщение (триал доминант-бота), осталось {trial_messages_left}")
                    return True
        else:
            message_count = user.message_count
            free_limit = user.free_messages_limit
            subscription_status = user.subscription_status
            subscription_ends_at = user.subscription_ends_at

            # Проверяем триал
            if user.trial_ends_at and user.trial_ends_at > now:
                trial_messages_left = user.messages_count_trial
                if trial_messages_left > 0:
                    logger.debug(
                        f"Пользователь {user_id} может отправить сообщение (триал обычного бота), осталось {trial_messages_left}")
                    return True

        if message_count < free_limit:
            remaining = free_limit - message_count
            logger.debug(f"Пользователь {user_id} может отправить {remaining} бесплатных сообщений для бота {bot_name}")
            return True

        if subscription_status == SubsStatus.active:
            result = subscription_ends_at and subscription_ends_at > now
            logger.debug(f"Пользователь {user_id} (активная подписка {bot_name}): {result}")
            return result

        if subscription_status == SubsStatus.grace_period:
            result = subscription_ends_at and subscription_ends_at > now
            logger.debug(f"Пользователь {user_id} (льготный период {bot_name}): {result}")
            return result

        if subscription_status == SubsStatus.cancelled:
            result = subscription_ends_at and subscription_ends_at > now
            logger.debug(f"Пользователь {user_id} (отменённая подписка {bot_name}): {result}")
            return result

        logger.debug(f"Пользователь {user_id} не может отправлять сообщения в боте {bot_name}")
        return False

    # -------------------------------------- DOMINANT ---------------------------------------
    @classmethod
    async def activate_subscription_dominator(cls, user_id: int, tier: SubsTier, days: int = 30):
        """Активирует подписку для доминант-бота"""
        logger.info(f"Активация подписки доминант-бота для пользователя {user_id}")
        async with async_session() as session:
            now = datetime.utcnow()
            ends_at = now + timedelta(days=days)

            await session.execute(
                update(User)
                .filter_by(user_id=user_id)
                .values(
                    subscription_status_dominator=SubsStatus.active,
                    subscription_tier_dominator=tier,
                    subscription_ends_at_dominator=ends_at,
                    has_started_subscription=True
                )
            )
            await session.commit()
            logger.info(f"Подписка доминант-бота для пользователя {user_id} активирована до {ends_at}")

    @classmethod
    async def change_subscription_status_dominator(cls, user_id: int, status: SubsStatus):
        """Изменяет статус подписки доминант-бота"""
        logger.warning(f"Изменение статуса подписки доминант-бота пользователя {user_id} на {status}")
        async with async_session() as session:
            await session.execute(
                update(User)
                .filter_by(user_id=user_id)
                .values(subscription_status_dominator=status)
            )
            await session.commit()
            logger.info(f"Статус подписки доминант-бота пользователя {user_id} изменён на {status}")

    @classmethod
    async def update_subscription_end_date_dominator(cls, user_id: int, new_end_date: datetime):
        """Обновляет дату окончания подписки доминант-бота"""
        logger.info(f"Обновление даты окончания подписки доминант-бота пользователя {user_id} на {new_end_date}")
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(subscription_ends_at_dominator=new_end_date)
            )
            await session.commit()

    @classmethod
    async def get_users_for_auto_charge_dominator(cls):
        logger.debug("Получение пользователей для автоматического списания (доминант)")
        async with async_session() as session:
            now = datetime.utcnow()
            three_days_ago = now - timedelta(days=3)

            result = await session.execute(
                select(User)
                .where(
                    User.subscription_status_dominator.in_([SubsStatus.active, SubsStatus.grace_period]),
                    User.payment_method_id.isnot(None),
                    User.subscription_ends_at_dominator <= now,
                    User.grace_period_attempts_dominator == 0,
                    or_(
                        User.subscription_status_dominator == SubsStatus.grace_period,
                        User.subscription_ends_at_dominator >= three_days_ago
                    )
                )
            )
            users = result.scalars().all()
            logger.debug(f"Найдено {len(users)} пользователей для автоматического списания (доминант)")
            return users

    # -------------------------------------- CRON ---------------------------------------
    @classmethod
    async def get_users_for_auto_charge(cls):
        logger.debug("Получение пользователей для автоматического списания")
        async with async_session() as session:
            now = datetime.utcnow()
            three_days_ago = now - timedelta(days=3)

            result = await session.execute(
                select(User)
                .where(
                    User.subscription_status.in_([SubsStatus.active.value, SubsStatus.grace_period.value]),
                    User.payment_method_id.isnot(None),
                    User.subscription_ends_at <= now,
                    User.grace_period_attempts == 0,  # ✅ ТОЛЬКО ТЕ, У КОГО НЕТ ПОПЫТОК
                    or_(
                        User.subscription_status == SubsStatus.grace_period,
                        User.subscription_ends_at >= three_days_ago
                    )
                )
            )
            users = result.scalars().all()
            logger.debug(f"Найдено {len(users)} пользователей для автоматического списания")
            return users

    @classmethod
    async def update_grace_period_attempts(cls, user_id: int, attempts: int):
        logger.debug(f"Обновление количества попыток льготного периода для пользователя {user_id}: {attempts}")
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(grace_period_attempts=attempts)
            )
            await session.commit()


class AudioService:
    @classmethod
    def recognize_from_s3(cls, filelink: str, api_key: str) -> str:
        import requests, time
        logger.info(f"Начало распознавания речи из файла: {filelink}")
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
            logger.error(f"Ошибка запуска распознавания: {resp.status_code} - {resp.text}")
            raise Exception(f"Ошибка старта: {resp.status_code} - {resp.text}")

        data = resp.json()
        operation_id = data['id']
        logger.debug(f"ID операции распознавания: {operation_id}")

        while True:
            time.sleep(5)
            resp = requests.get(f'https://operation.api.cloud.yandex.net/operations/{operation_id}', headers=headers)
            data = resp.json()
            if data.get('done'):
                break

        texts = [chunk['alternatives'][0]['text'] for chunk in data['response']['chunks']]
        result = ' '.join(texts)
        logger.info(f"Распознавание завершено, длина текста: {len(result)} символов")
        logger.debug(f"Распознанный текст: {result[:100]}...")
        return result
