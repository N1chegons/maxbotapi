from contextlib import asynccontextmanager
from fastapi import BackgroundTasks, FastAPI, Request, Response
from src.vk_bot.bot_instance import bot

# Хардкодим код подтверждения (тот, что показывает ВК)
confirmation_code = "1ce68d2b"
secret_key: str = "" # сюда можно вставить секретный ключ из настроек Callback API, если он там включен

@asynccontextmanager
async def lifespan(app: FastAPI):
    global secret_key
    # Если setup_webhook нужен для получения secret_key, оставь его, но confirmation_code уже жестко задан
    try:
        _, secret_key = await bot.setup_webhook()
    except Exception as e:
        print(f"Ошибка setup_webhook: {e}")
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/vk_webhook")
async def vk_handler(req: Request, background_task: BackgroundTasks):
    try:
        data = await req.json()
    except Exception:
        return Response("not today", status_code=403)

    if data["type"] == "confirmation":
        return Response(confirmation_code) # Теперь вернет 1ce68d2b

    if data.get("secret") == secret_key or not secret_key: # Если секрет не задан, пропускаем
        background_task.add_task(bot.process_event, data)
    return Response("ok")