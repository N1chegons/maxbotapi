from aiohttp import web
from vkbottle import Bot
from vkbottle.callback import BotCallback

from src.config import settings
from src.vk_bot.quizs_handler.fact_handler.fact import fact_labeler
from src.vk_bot.quizs_handler.menu_handler import menu_labeler

VK_TOKEN = settings.VK_TOKEN_COMMUNITY
VK_URL = "https://bot.nepovinnyh.ru/vk_webhook"

app = web.Application()
callback = BotCallback(
    url=VK_URL,
    title="vk_bot",
    secret_key=settings.VK_SECRET,
)

bot = Bot(token=VK_TOKEN, callback=callback)
bot.labeler.load(menu_labeler)
bot.labeler.load(fact_labeler)
