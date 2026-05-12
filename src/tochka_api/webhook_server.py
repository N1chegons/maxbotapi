from aiohttp import web
import json
import logging

logging.basicConfig(level=logging.INFO)


async def handle_tochka(request):
    body = await request.text()
    print("🔔 Получен вебхук от Точки:", body)

    # 2. Парсим JSON
    try:
        data = json.loads(body)
    except:
        data = {}

    # 3. Если это тестовый вебхук — просто логируем
    if data.get('webhookType') == 'incomingPayment':
        print("✅ Получен платёжный вебхук")
        # Здесь потом будешь активировать подписку

    # 4. Всегда отвечаем 200 OK
    return web.Response(status=200, text="OK")


# Создаём приложение и роуты
app = web.Application()
app.router.add_post('/tochka/webhook', handle_tochka)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8084)