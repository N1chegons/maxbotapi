from vkbottle import API, BuiltinStateDispenser, Bot
from vkbottle.bot import BotLabeler
from vkbottle.callback import BotCallback
from src.config import settings

import src.vk_bot.quizs_handler.menu_handler
import src.vk_bot.quizs_handler.fact_handler.fact
import src.vk_bot.quizs_handler.opinions_handler.opinions
import src.vk_bot.admin_handler.admin

labeler = BotLabeler()

api = API(settings.VK_TOKEN_COMMUNITY)
state_dispenser = BuiltinStateDispenser()

callback = BotCallback(
    url="https://bot.nepovinnyh.ru/vk_webhook",
    title="vk_bot",
    secret_key=settings.VK_SECRET
)

bot = Bot(
    api=api,
    labeler=labeler,
    state_dispenser=state_dispenser,
    callback=callback
)