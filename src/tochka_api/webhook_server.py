import sys
from datetime import datetime, timedelta
import json

from aiohttp import web
import jwt
from jwt import exceptions

project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.max.repository import MaxService
from src.tochka_api.service import TochkaApiService
from src.max.models import SubsTier, SubsStatus, UserState, PaymentStatus
from src.logger_config import setup_logger

logger = setup_logger('webhook_tochka', 'tochka_api', 'webhook_server.log')

# Публичный ключ Точки
KEY_JSON = '{"kty":"RSA","e":"AQAB","n":"rwm77av7GIttq-JF1itEgLCGEZW_zz16RlUQVYlLbJtyRSu61fCec_rroP6PxjXU2uLzUOaGaLgAPeUZAJrGuVp9nryKgbZceHckdHDYgJd9TsdJ1MYUsXaOb9joN9vmsCscBx1lwSlFQyNQsHUsrjuDk-opf6RCuazRQ9gkoDCX70HV8WBMFoVm-YWQKJHZEaIQxg_DU4gMFyKRkDGKsYKA0POL-UgWA1qkg6nHY5BOMKaqxbc5ky87muWB5nNk4mfmsckyFv9j1gBiXLKekA_y4UwG2o1pbOLpJS3bP_c95rm4M9ZBmGXqfOQhbjz8z-s9C11i-jmOQ2ByohS-ST3E5sqBzIsxxrxyQDTw--bZNhzpbciyYW4GfkkqyeYoOPd_84jPTBDKQXssvj8ZOj2XboS77tvEO1n1WlwUzh8HPCJod5_fEgSXuozpJtOggXBv0C2ps7yXlDZf-7Jar0UYc_NJEHJF-xShlqd6Q3sVL02PhSCM-ibn9DN9BKmD"}'
key = json.loads(KEY_JSON)
jwk_key = jwt.jwk_from_dict(key)


async def handle_webhook(request):
    body = await request.text()
    logger.info(f"🔔 Вебхук получен: {body[:200]}")

    try:
        decoded = jwt.JWT().decode(body, key=jwk_key)
        logger.info(f"✅ Расшифровано: {decoded}")

        webhook_type = decoded.get('webhookType')
        status = decoded.get('status')
        operation_id = decoded.get('operationId')
        amount = decoded.get('amount')

        logger.info(f"Тип: {webhook_type}, Статус: {status}, operationId: {operation_id}")

        if webhook_type != 'acquiringInternetPayment':
            return web.Response(status=200, text="OK")

        user_id = await TochkaApiService.find_user_by_operation_id(operation_id)
        if not user_id:
            logger.warning(f"⚠️ Пользователь не найден для operation_id: {operation_id}")
            return web.Response(status=200, text="OK")

        user = await MaxService.get_user(user_id)
        if not user:
            logger.warning(f"⚠️ Пользователь {user_id} не найден в БД")
            return web.Response(status=200, text="OK")

        if status == 'APPROVED':
            await MaxService.save_payment_method(user_id, operation_id)
            logger.info(f"💳 Сохранён токен карты (operationId) для {user_id}")

            if user.subscription_status == SubsStatus.active and user.subscription_ends_at:
                new_end_date = user.subscription_ends_at + timedelta(days=31)
            else:
                # noinspection PyDeprecation
                new_end_date = datetime.utcnow() + timedelta(days=31)

            await MaxService.update_subscription_end_date(user_id, new_end_date)
            await MaxService.activate_subscription(user_id, SubsTier.basic, UserState.PAID)
            await MaxService.change_subscription_status(user_id, SubsStatus.active)
            await TochkaApiService.update_status_payment(operation_id, PaymentStatus.succeeded)
            logger.info(f"✅ Подписка активна для {user_id} до {new_end_date}")

        else:
            await TochkaApiService.update_status_payment(operation_id, PaymentStatus.failed)
            logger.warning(f"❌ Платёж {operation_id} не удался, статус: {status}")

    except exceptions.JWTDecodeError:
        logger.error("❌ Ошибка: неверная подпись JWT")
        return web.Response(status=400, text="Invalid signature")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

    return web.Response(status=200, text="OK")


async def handle_consult_form(request: web.Request):
    try:
        data = await request.json()
        contact = data.get('contact', 'Не указан')
        question = data.get('question', 'Не указан')

        appointment_date = await MaxService.get_next_free_date()
        # noinspection PyTypeChecker
        await MaxService.add_request(
            client_id=None,
            contact=contact,
            messages=question,
            appointment_date=appointment_date
        )

        return web.json_response(
            {"status": "ok"},
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            }
        )
    except Exception as e:
        print(f"Ошибка: {e}")
        return web.json_response(
            {"status": "error"},
            status=500,
            headers={
                'Access-Control-Allow-Origin': '*',
            }
        )


async def handle_options(request: web.Request):
    return web.Response(
        status=200,
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
    )



app = web.Application()
app.router.add_post('/tochka_api/webhook', handle_webhook)
app.router.add_options('/api/consult', handle_options)
app.router.add_post('/api/consult', handle_consult_form)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8084)