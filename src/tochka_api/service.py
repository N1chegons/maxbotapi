import http.client
import json

from sqlalchemy import select, insert

from src.config import settings
from src.db import async_session
from src.max.models import Payment

conn = http.client.HTTPSConnection("enter.tochka.com")

class TochkaApiService:
    def __init__(self):
        self.jwt_tochka_api = settings.JWT_TOKEN_TOCHKA_API
        self.account_id = settings.TOCHKA_ACCOUNT_DATA
        self.customer_code = settings.CUSTOMER_CODE

    @classmethod
    async def find_user_by_operation_id(cls, operation_id: str) -> int:
        async with async_session() as session:
            result = await session.execute(
                select(Payment.user_id).where(Payment.payment_id == operation_id)
            )
            return result.scalar_one_or_none()

    @classmethod
    async def save_payment(cls, user_id: int, operation_id: str, payment_link: str, amount: float):
        async with async_session() as session:
            stmt = insert(Payment).values(
                payment_id=operation_id,
                user_id=user_id,
                amount=amount,
            )
            await session.execute(stmt)
            await session.commit()


    def create_payment_link(self, amount: float, user_id: int):
        payload = json.dumps({
            "Data": {
                "customerCode": f"{self.customer_code}",
                "amount": amount,
                "purpose": f"Оплата подписки на бота для пользователя {user_id}",
                "paymentMode": ["card"],
                "saveCard": True,
                "merchantId": "200000000037987",
                "preAuthorization": False,
                "ttl": 1000
            }
        })

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.jwt_tochka_api}'
        }

        conn.request("POST", "https://enter.tochka.com/uapi/acquiring/v1.0/payments", payload, headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))

        operation_id = data.get("Data", {}).get("operationId")
        payment_link = data.get("Data", {}).get("paymentLink")

        return {
            "payment_id": operation_id,
            "payment_link": payment_link
        }


