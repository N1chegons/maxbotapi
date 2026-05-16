import http.client
import json

from sqlalchemy import select, insert, update

from src.config import settings
from src.db import async_session
from src.max.models import Payment, PaymentStatus

conn = http.client.HTTPSConnection("enter.tochka.com")

class TochkaApiService:
    def __init__(self):
        self.jwt_tochka_api = settings.JWT_TOKEN_TOCHKA_API
        self.account_id = settings.TOCHKA_ACCOUNT_DATA
        self.customer_code = settings.CUSTOMER_CODE

    @classmethod
    async def find_operation(cls, operation_id: str):
        async with async_session() as session:
            result = await session.execute(
                select(Payment).where(Payment.payment_id == operation_id)
            )
            return result

    @classmethod
    async def find_user_by_operation_id(cls, operation_id: str) -> int:
        async with async_session() as session:
            result = await session.execute(
                select(Payment.user_id).where(Payment.payment_id == operation_id)
            )
            return result.scalar_one_or_none()

    @classmethod
    async def save_payment(cls, user_id: int, operation_id: str, amount: float):
        async with async_session() as session:
            stmt = insert(Payment).values(
                payment_id=operation_id,
                user_id=user_id,
                amount=amount,
            )
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def update_status_payment(cls, operation_id: str):
        async with async_session() as session:
            stmt = update(Payment).filter_by(payment_id=operation_id).values(status=PaymentStatus.succeeded)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def get_last_payment(cls, user_id: int):
        async with async_session() as session:
            result = await session.execute(
                select(Payment)
                .where(Payment.user_id == user_id)
                .order_by(Payment.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    def create_payment_link(self, amount: float, user_id: int, platform: str):
        payload = json.dumps({
            "Data": {
                "customerCode": f"{self.customer_code}",
                "amount": amount,
                "purpose": "Оплата подписки на бота для пользователя",
                "saveCard": True,
                "recurring": True,
                "paymentLinkId": f"Payment user by {platform} id: {user_id}"
            }
        })

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.jwt_tochka_api}'
        }

        conn.request("POST", "/uapi/acquiring/v1.0/subscriptions", payload, headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))

        operation_id = data.get("Data", {}).get("operationId")
        payment_link = data.get("Data", {}).get("paymentLink")

        return {
            "payment_id": operation_id,
            "payment_link": payment_link
        }

    def charge_payments(self, amount: float, operation_id: str):
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
        conn.request("POST", f"/uapi/acquiring/v1.0/subscriptions/{operation_id}/charge", payload, headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))

        operation_id = data.get("Data", {}).get("result")

        return operation_id
