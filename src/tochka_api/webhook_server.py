from aiohttp import web
import json
import logging

logging.basicConfig(level=logging.INFO)


async def handle_tochka(request):
    """Принимает вебхук от Точки и печатает в консоль"""
    body = await request.text()
    print("Вебхук Точки:", body)

    # Всегда отвечаем 200 OK
    return web.Response(status=200, text="OK")


# Создаём приложение и роуты
app = web.Application()
app.router.add_post('/tochka/webhook', handle_tochka)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8084)