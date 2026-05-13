from aiohttp import web
import json
import logging

project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.max.repository import MaxService
from src.tochka_api.service import TochkaApiService

logging.basicConfig(level=logging.INFO)


async def handle_tochka(request):
    body = await request.text()
    print("🔔 Получен вебхук от Точки:", body)

    # 2. Парсим JSON
    try:
        data = json.loads(body)
        if data.get('status') == 'SUCCEEDED':
            operation_id = data.get('operationId')
            if operation_id:
                # Ищем пользователя по operation_id
                user_id = await TochkaApiService.find_user_by_operation_id(operation_id)
                if user_id:
                    await MaxService.activate_subscription(user_id)
                    print(f"✅ Подписка активирована для user_id {user_id}")
                else:
                    print(f"⚠️ Пользователь для operation_id {operation_id} не найден")
    except Exception as e:
        print("❌ Ошибка обработки вебхука:", e)

    return web.Response(status=200, text="OK")


# Создаём приложение и роуты
app = web.Application()
app.router.add_post('/tochka/webhook', handle_tochka)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8084)