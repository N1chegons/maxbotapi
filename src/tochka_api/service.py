import http.client
import json

from sqlalchemy import select, insert, update

from src.config import settings
from src.db import async_session
from src.logger_config import setup_logger
from src.max.models import Payment, PaymentStatus

logger = setup_logger('service_tochka', 'tochka_api', 'service_tochka.log')

conn = http.client.HTTPSConnection("enter.tochka.com")


class TochkaApiService:
    def __init__(self):
        self.jwt_tochka_api = settings.JWT_TOKEN_TOCHKA_API
        self.account_id = settings.TOCHKA_ACCOUNT_DATA
        self.customer_code = settings.CUSTOMER_CODE
        logger.debug("Инициализация TochkaApiService")

    @classmethod
    async def find_operation(cls, operation_id: str):
        logger.debug(f"Поиск операции {operation_id} в БД")
        async with async_session() as session:
            result = await session.execute(
                select(Payment).where(Payment.payment_id == operation_id)
            )
            return result

    @classmethod
    async def find_user_by_operation_id(cls, operation_id: str) -> int:
        logger.debug(f"Поиск пользователя по operation_id: {operation_id}")
        async with async_session() as session:
            result = await session.execute(
                select(Payment.user_id).where(Payment.payment_id == operation_id)
            )
            user_id = result.scalar_one_or_none()
            if user_id:
                logger.debug(f"Найден пользователь {user_id} для operation_id {operation_id}")
            else:
                logger.debug(f"Пользователь для operation_id {operation_id} не найден")
            return user_id

    @classmethod
    async def save_payment(cls, user_id: int, operation_id: str, amount: float):
        logger.info(f"Сохранение платежа: user_id={user_id}, operation_id={operation_id}, amount={amount}")
        async with async_session() as session:
            stmt = insert(Payment).values(
                payment_id=operation_id,
                user_id=user_id,
                amount=amount,
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Платёж {operation_id} для пользователя {user_id} успешно сохранён")

    @classmethod
    async def update_status_payment(cls, operation_id: str, payment_status: PaymentStatus):
        logger.info(f"Обновление статуса платежа {operation_id} на {payment_status}")
        async with async_session() as session:
            stmt = update(Payment).filter_by(payment_id=operation_id).values(status=payment_status)
            await session.execute(stmt)
            await session.commit()
            logger.debug(f"Статус платежа {operation_id} обновлён")

    @classmethod
    async def get_last_payment(cls, user_id: int):
        logger.debug(f"Получение последнего платежа для пользователя {user_id}")
        async with async_session() as session:
            result = await session.execute(
                select(Payment)
                .where(Payment.user_id == user_id)
                .order_by(Payment.created_at.desc())
                .limit(1)
            )
            payment = result.scalar_one_or_none()
            if payment:
                logger.debug(f"Найден последний платёж {payment.payment_id} для пользователя {user_id}")
            else:
                logger.debug(f"Платежей для пользователя {user_id} не найдено")
            return payment

    def create_payment_link(self, amount: float):
        logger.info(f"Создание ссылки на оплату на сумму {amount} руб.")
        payload = json.dumps({
            "Data": {
                "customerCode": f"{self.customer_code}",
                "amount": amount,
                "purpose": "Оплата подписки на бота для пользователя",
                "saveCard": True,
                "recurring": True,
            }
        })

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.jwt_tochka_api}'
        }

        try:
            conn.request("POST", "/uapi/acquiring/v1.0/subscriptions", payload, headers)
            res = conn.getresponse()
            data = json.loads(res.read().decode("utf-8"))

            operation_id = data.get("Data", {}).get("operationId")
            payment_link = data.get("Data", {}).get("paymentLink")

            if operation_id and payment_link:
                logger.info(f"Ссылка на оплату создана: operation_id={operation_id}, link={payment_link}")
            else:
                logger.warning(f"Не удалось получить operation_id или payment_link: {data}")

            return {
                "payment_id": operation_id,
                "payment_link": payment_link
            }
        except Exception as e:
            logger.error(f"Ошибка при создании ссылки на оплату: {e}")
            raise

    def charge_payments(self, amount: float, operation_id: str):
        logger.info(f"Списание средств: сумма={amount}, operation_id={operation_id}")
        payload = json.dumps({
            "Data": {
                "amount": amount
            }
        })
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.jwt_tochka_api}'
        }

        try:
            conn.request("POST", f"/uapi/acquiring/v1.0/subscriptions/{operation_id}/charge", payload, headers)
            res = conn.getresponse()
            data = json.loads(res.read().decode("utf-8"))

            result_operation_id = data.get("Data", {}).get("result")

            if result_operation_id:
                logger.info(f"Списание успешно выполнено, operation_id: {result_operation_id}")
            else:
                logger.warning(f"Не удалось получить result при списании: {data}")

            return result_operation_id
        except Exception as e:
            logger.error(f"Ошибка при списании средств: {e}")
            raise