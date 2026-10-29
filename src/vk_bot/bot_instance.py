from vkbottle import Bot, BuiltinStateDispenser
from vkbottle.callback import BotCallback
from src.config import settings

state_dispenser = BuiltinStateDispenser()

callback = BotCallback(
    url="https://bot.nepovinnyh.ru/vk_webhook",
    title="vk_bot",
    secret_key=settings.VK_SECRET
)

bot = Bot(
    token=settings.VK_TOKEN_COMMUNITY,
    callback=callback,
    state_dispenser=state_dispenser
)