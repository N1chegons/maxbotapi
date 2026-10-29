from src.vk_bot.admin_handler.admin import admin_labeler
from src.vk_bot.bot_instance import bot
from src.vk_bot.quizs_handler.fact_handler.fact import fact_labeler
from src.vk_bot.quizs_handler.menu_handler import menu_labeler

bot.labeler.load(menu_labeler)
bot.labeler.load(fact_labeler)
bot.labeler.load(admin_labeler)
