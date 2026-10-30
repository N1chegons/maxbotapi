from vkbottle import API, BuiltinStateDispenser, Bot
from vkbottle.bot import BotLabeler
from vkbottle.callback import BotCallback
from src.config import settings

# Создаем пустые объекты
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