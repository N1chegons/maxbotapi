import sys
import datetime
import json
import logging
from aiohttp import web
import jwt
from jwt import exceptions

project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.max.repository import MaxService
from src.tochka_api.service import TochkaApiService
from src.max.models import SubsTier, SubsStatus, UserState, PaymentStatus
from src.telegram.bot import show_chat_tg
from src.max.bot import show_chat

logging.basicConfig(level=logging.INFO)

# Публичный ключ Точки
KEY_JSON = '{"kty":"RSA","e":"AQAB","n":"rwm77av7GIttq-JF1itEgLCGEZW_zz16RlUQVYlLbJtyRSu61fCec_rroP6PxjXU2uLzUOaGaLgAPeUZAJrGuVp9nryKgbZceHckdHDYgJd9TsdJ1MYUsXaOb9joN9vmsCscBx1lwSlFQyNQsHUsrjuDk-opf6RCuazRQ9gkoDCX70HV8WBMFoVm-YWQKJHZEaIQxg_DU4gMFyKRkDGKsYKA0POL-UgWA1qkg6nHY5BOMKaqxbc5ky87muWB5nNk4mfmsckyFv9j1gBiXLKekA_y4UwG2o1pbOLpJS3bP_c95rm4M9ZBmGXqfOQhbjz8z-s9C11i-jmOQ2ByohS-ST3E5sqBzIsxxrxyQDTw--bZNhzpbciyYW4GfkkqyeYoOPd_84jPTBDKQXssvj8ZOj2XboS77tvEO1n1WlwUzh8HPCJod5_fEgSXuozpJtOggXBv0C2ps7yXlDZf-7Jar0UYc_NJEHJF-xShlqd6Q3sVL02PhSCM-ibn9DN9BKmD"}'
key = json.loads(KEY_JSON)
jwk_key = jwt.jwk_from_dict(key)


async def handle_webhook(request):
    body = await request.text()
    logging.info(f"🔔 Вебхук получен: {body[:200]}")

    try:
        decoded = jwt.JWT().decode(body, key=jwk_key)
        logging.info(f"✅ Расшифровано: {decoded}")

        webhook_type = decoded.get('webhookType')
        status = decoded.get('status')
        operation_id = decoded.get('operationId')
        amount = decoded.get('amount')

        logging.info(f"Тип: {webhook_type}, Статус: {status}, operationId: {operation_id}")

        if webhook_type != 'acquiringInternetPayment':
            return web.Response(status=200, text="OK")

        user_id = await TochkaApiService.find_user_by_operation_id(operation_id)
        if not user_id:
            logging.warning(f"⚠️ Пользователь не найден для operation_id: {operation_id}")
            return web.Response(status=200, text="OK")

        user = await MaxService.get_user(user_id)
        if not user:
            logging.warning(f"⚠️ Пользователь {user_id} не найден в БД")
            return web.Response(status=200, text="OK")

        if status == 'APPROVED':
            await MaxService.save_payment_method(user_id, operation_id)
            logging.info(f"💳 Сохранён токен карты (operationId) для {user_id}")

            if float(amount) == 14.00:
                await MaxService.mark_started_subscription(user_id)
                await MaxService.start_trial(user_id)
                await MaxService.change_subscription_status(user_id, SubsStatus.trial)
                logging.info(f"📆 Триал активирован для {user_id}")
                await TochkaApiService.update_status_payment(operation_id, PaymentStatus.succeeded)

                if user.platform == "MAX":
                    await show_chat(user_id)
                else:
                    await show_chat_tg(user_id)

            else:
                if user.subscription_status == SubsStatus.active and user.subscription_ends_at:
                    new_end_date = user.subscription_ends_at + datetime.timedelta(days=31)
                else:
                    new_end_date = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=31)

                await MaxService.update_subscription_end_date(user_id, new_end_date)
                await MaxService.activate_subscription(user_id, SubsTier.basic, UserState.PAID)
                await MaxService.change_subscription_status(user_id, SubsStatus.active)
                await TochkaApiService.update_status_payment(operation_id, PaymentStatus.succeeded)
                logging.info(f"✅ Подписка активна для {user_id} до {new_end_date}")

        else:
            await TochkaApiService.update_status_payment(operation_id, PaymentStatus.failed)
            logging.warning(f"❌ Платёж {operation_id} не удался, статус: {status}")

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