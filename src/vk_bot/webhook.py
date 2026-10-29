from bot import bot
from fastapi import BackgroundTasks, FastAPI, Request, Response

app = FastAPI()

confirmation_code: str
secret_key: str

@app.on_event("startup")
async def startup_event():
    global confirmation_code, secret_key
    confirmation_code, secret_key = await bot.setup_webhook()


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