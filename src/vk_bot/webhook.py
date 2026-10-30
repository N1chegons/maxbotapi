from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Request, Response

from src.vk_bot.bot_instance import bot

confirmation_code: str
secret_key: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    global confirmation_code, secret_key
    confirmation_code, secret_key = await bot.setup_webhook()
    yield


app = FastAPI(lifespan=lifespan)

@app.post("/vk_webhook")
async def vk_handler(req: Request, background_task: BackgroundTasks):
    try:
        data = await req.json()
    except Exception:
        return Response("not today", status_code=403)

    if data["type"] == "confirmation":
        return Response(confirmation_code)

    if data["secret"] == secret_key:
        background_task.add_task(bot.process_event, data)
    return Response("ok")


import src.vk_bot.quizs_handler.menu_handler
import src.vk_bot.quizs_handler.fact_handler.fact
import src.vk_bot.quizs_handler.opinions_handler.opinions
import src.vk_bot.admin_handler.admin
import src.vk_bot.quizs_handler.create_message_event
import src.vk_bot.quizs_handler.test_handler.test