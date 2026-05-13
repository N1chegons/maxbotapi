from aiohttp import web
import jwt
from jwt import exceptions
import json
import logging
import sys


project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.max.repository import MaxService
from src.tochka_api.service import TochkaApiService
from src.max.models import SubsTier

# Публичный ключ Точки (получен из документации)
key_json = '{"kty":"RSA","e":"AQAB","n":"rwm77av7GIttq-JF1itEgLCGEZW_zz16RlUQVYlLbJtyRSu61fCec_rroP6PxjXU2uLzUOaGaLgAPeUZAJrGuVp9nryKgbZceHckdHDYgJd9TsdJ1MYUsXaOb9joN9vmsCscBx1lwSlFQyNQsHUsrjuDk-opf6RCuazRQ9gkoDCX70HV8WBMFoVm-YWQKJHZEaIQxg_DU4gMFyKRkDGKsYKA0POL-UgWA1qkg6nHY5BOMKaqxbc5ky87muWB5nNk4mfmsckyFv9j1gBiXLKekA_y4UwG2o1pbOLpJS3bP_c95rm4M9ZBmGXqfOQhbjz8z-s9C11i-jmOQ2ByohS-ST3E5sqBzIsxxrxyQDTw--bZNhzpbciyYW4GfkkqyeYoOPd_84jPTBDKQXssvj8ZOj2XboS77tvEO1n1WlwUzh8HPCJod5_fEgSXuozpJtOggXBv0C2ps7yXlDZf-7Jar0UYc_NJEHJF-xShlqd6Q3sVL02PhSCM-ibn9DN9BKmD"}'
key = json.loads(key_json)
jwk_key = jwt.jwk_from_dict(key)


async def handle(request: web.Request):
    body = await request.text()
    print("🔔 Вебхук Точки:", body)

    # 2. Проверяем подпись (отклоняем левые запросы)
    try:
        decoded = jwt.JWT().decode(body, key=jwk_key, do_verify=True)
        print("✅ Подпись верна")
    except exceptions.JWTDecodeError:
        print("❌ Неверная подпись")
        return web.Response(status=400, text="Invalid signature")

    # 3. Обрабатываем успешный платёж
    status = decoded.get('status')
    if status == 'APPROVED' or status == 'SUCCEEDED':
        payment_link_id = decoded.get('paymentLinkId')
        if payment_link_id:
            # Ищем пользователя по payment_link_id (он у тебя хранится в БД)
            user_id = await TochkaApiService.find_user_by_operation_id(payment_link_id)
            if user_id:
                await MaxService.activate_subscription(user_id, SubsTier.basic)
                print(f"✅ Подписка активирована для {user_id}")
            else:
                print(f"⚠️ Пользователь для payment_link_id {payment_link_id} не найден")

    # 4. Всегда отвечаем 200 OK
    return web.Response(status=200, text="OK")

app = web.Application()
app.router.add_route("POST", '/tochka_api/webhook', handle)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8084)