from aiohttp import web
import jwt
from jwt import exceptions
import json
import logging

# Публичный ключ Точки (получен из документации)
key_json = '{"kty":"RSA","e":"AQAB","n":"rwm77av7GIttq-JF1itEgLCGEZW_zz16RlUQVYlLbJtyRSu61fCec_rroP6PxjXU2uLzUOaGaLgAPeUZAJrGuVp9nryKgbZceHckdHDYgJd9TsdJ1MYUsXaOb9joN9vmsCscBx1lwSlFQyNQsHUsrjuDk-opf6RCuazRQ9gkoDCX70HV8WBMFoVm-YWQKJHZEaIQxg_DU4gMFyKRkDGKsYKA0POL-UgWA1qkg6nHY5BOMKaqxbc5ky87muWB5nNk4mfmsckyFv9j1gBiXLKekA_y4UwG2o1pbOLpJS3bP_c95rm4M9ZBmGXqfOQhbjz8z-s9C11i-jmOQ2ByohS-ST3E5sqBzIsxxrxyQDTw--bZNhzpbciyYW4GfkkqyeYoOPd_84jPTBDKQXssvj8ZOj2XboS77tvEO1n1WlwUzh8HPCJod5_fEgSXuozpJtOggXBv0C2ps7yXlDZf-7Jar0UYc_NJEHJF-xShlqd6Q3sVL02PhSCM-ibn9DN9BKmD"}'
key = json.loads(key_json)
jwk_key = jwt.jwk_from_dict(key)


async def handle(request: web.Request):
    # payload = await request.text()
    #
    # try:
    #     # тело вебхука
    #     webhook_jwt = jwt.JWT().decode(
    #         message=payload,
    #         key=jwk_key,
    #     )
    #     return web.Response(status=200, text="OK")
    # except exceptions.JWTDecodeError:
    #     pass
    #
    return web.Response(status=200, text="OK")

app = web.Application()
app.router.add_route("POST", '/tochka_api/webhook', handle)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8084)