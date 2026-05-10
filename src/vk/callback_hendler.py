# from aiohttp import web
# import json
#
# VK_CONFIRMATION_CODE = "5acbfb67"
# VK_SECRET_KEY = "aaQ13axAPQEcczQa"
#
# app = web.Application()
#
#
# async def vk_callback_handler(request):
#     # Проверка секрета
#     received_secret = request.headers.get('X-VK-API-Secret')
#     if received_secret != VK_SECRET_KEY:
#         return web.Response(status=403)
#
#     data = await request.json()
#     event_type = data.get('type')
#
#     # Подтверждение сервера
#     if event_type == 'confirmation':
#         return web.Response(text="5acbfb67", status=200)
#
#     # Обработка событий
#     elif event_type == 'wall_post_new':
#         # Появился новый пост на стене (возможно с видео)
#         print("Новый пост в группе!")
#         # Здесь можно парсить видео и отправлять в канал MAX
#         # ...
#         return web.Response(text='ok', status=200)
#
#     return web.Response(text='ok', status=200)
#
#
# app.router.add_post('/vk/callback', vk_callback_handler)
#
# if __name__ == '__main__':
#     web.run_app(app, host='127.0.0.1', port=8083)
#
from aiohttp import web

app = web.Application()

async def handler(request):
    print("Запрос получен!")
    return web.Response(text="5acbfb67", status=200)

app.router.add_post('/vk/callback', handler)

if __name__ == "__main__":
    web.run_app(app, host='127.0.0.1', port=8083)