from aiohttp import web
from vkbottle import Bot
from vkbottle.callback import BotCallback

from src.config import settings
from src.vk_bot.quizs_handler.fact_handler.fact import fact_labeler
from src.vk_bot.quizs_handler.menu_handler import menu_labeler

VK_TOKEN = settings.VK_TOKEN_COMMUNITY
VK_URL = "https://bot.nepovinnyh.ru/vk_webhook"

callback = BotCallback(
    url=VK_URL,
    title="vk_bot",
    secret_key=settings.VK_SECRET,
)

bot = Bot(token=VK_TOKEN, callback=callback)
bot.labeler.load(menu_labeler)
bot.labeler.load(fact_labeler)

# Создаем веб-приложение aiohttp
app = web.Application()


async def vk_webhook_handler(request: web.Request):
    data = await request.post()
    event_data = dict(data)

    await bot.process_event(event_data)
    return web.Response(text="fcd13d3b")

# Регистрируем путь для вебхука
app.router.add_post("/vk_webhook", vk_webhook_handler)

if __name__ == "__main__":
    print("ВК-бот (Webhook) запущен на порту 8085")
    web.run_app(app, host="0.0.0.0", port=8085)