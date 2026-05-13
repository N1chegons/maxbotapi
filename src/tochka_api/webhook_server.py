import sys

from aiohttp import web
import jwt
from jwt import exceptions
import json
import logging
project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.max.models import SubsTier, SubsStatus
from src.max.repository import MaxService
from src.config import settings
from src.tochka_api.service import TochkaApiService

logging.basicConfig(level=logging.INFO)

# Публичный ключ Точки
KEY_JSON = '{"kty":"RSA","e":"AQAB","n":"rwm77av7GIttq-JF1itEgLCGEZW_zz16RlUQVYlLbJtyRSu61fCec_rroP6PxjXU2uLzUOaGaLgAPeUZAJrGuVp9nryKgbZceHckdHDYgJd9TsdJ1MYUsXaOb9joN9vmsCscBx1lwSlFQyNQsHUsrjuDk-opf6RCuazRQ9gkoDCX70HV8WBMFoVm-YWQKJHZEaIQxg_DU4gMFyKRkDGKsYKA0POL-UgWA1qkg6nHY5BOMKaqxbc5ky87muWB5nNk4mfmsckyFv9j1gBiXLKekA_y4UwG2o1pbOLpJS3bP_c95rm4M9ZBmGXqfOQhbjz8z-s9C11i-jmOQ2ByohS-ST3E5sqBzIsxxrxyQDTw--bZNhzpbciyYW4GfkkqyeYoOPd_84jPTBDKQXssvj8ZOj2XboS77tvEO1n1WlwUzh8HPCJod5_fEgSXuozpJtOggXBv0C2ps7yXlDZf-7Jar0UYc_NJEHJF-xShlqd6Q3sVL02PhSCM-ibn9DN9BKmD"}'
key = json.loads(KEY_JSON)
jwk_key = jwt.jwk_from_dict(key)

async def handle_webhook(request):
    body = await request.text()
    logging.info(f"🔔 Вебхук получен: {body[:200]}")

    try:
        # Расшифровываем JWT
        decoded = jwt.JWT().decode(body, key=jwk_key)
        logging.info(f"✅ Расшифровано: {decoded}")

        # Извлекаем поля (строго по документации)
        webhook_type = decoded.get('webhookType')
        status = decoded.get('status')
        payment_link_id = decoded.get('operationId')
        operation_id = decoded.get('operationId')
        payment_method_id = decoded.get('paymentMethodId')


        logging.info(f"Тип: {webhook_type}, Статус: {status}, paymentLinkId: {payment_link_id}")

        if webhook_type == 'acquiringInternetPayment' and status == 'APPROVED':
            if payment_link_id:
                user_id = await TochkaApiService.find_user_by_operation_id(payment_link_id)
                if user_id:
                    await MaxService.activate_subscription(user_id, SubsTier.basic)
                    await MaxService.change_subscription_status(user_id, SubsStatus.trial)
                    await TochkaApiService.update_status_payment(operation_id)
                    if payment_method_id:
                        await MaxService.save_payment_method(user_id, payment_method_id)
                        logging.info(f"💳 Сохранён токен карты: {payment_method_id}")
                    else:
                        logging.info("ℹ️ Клиент не сохранил карту")
                    logging.info(f"✅ Подписка активирована для {user_id}")
                else:
                    logging.warning(f"⚠️ Пользователь не найден для payment_link_id: {payment_link_id}")
            else:
                logging.warning("⚠️ paymentLinkId отсутствует в вебхуке")

    except exceptions.JWTDecodeError:
        logging.error("❌ Ошибка: неверная подпись JWT")
        return web.Response(status=400, text="Invalid signature")
    except Exception as e:
        logging.error(f"❌ Ошибка: {e}")

    return web.Response(status=200, text="OK")

app = web.Application()
app.router.add_post('/tochka_api/webhook', handle_webhook)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8084)