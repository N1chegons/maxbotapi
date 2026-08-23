import asyncio
import subprocess

import aiohttp
import magic
from maxapi import Bot, Dispatcher, F
from maxapi.types import MessageCreated, BotStarted

from src.config import settings
from src.logger_config import setup_logger
from src.max.models import UserState
from src.max.repository import MaxService, AudioService
from src.max.utils import upload_to_s3
from src.yandexai.config import THEMES_INDEXES
from src.yandexai.orchestrator import ask_ai_with_index

logger = setup_logger('max_bot', 'max-2', 'MAX2_bot.log')

TOKEN = settings.MAX_BOT_TOKEN_2

bot = Bot(TOKEN)
dp = Dispatcher()

# logic
@dp.bot_started()
async def bot_started(event: BotStarted):
    user_id = event.user.user_id
    user = await MaxService.get_user(user_id)
    logger.info(f"Пользователь {user_id} запустил бота-2")

    if not user:
        await MaxService.create_user(user_id, "MAX")
        await MaxService.create_session(user_id)
        logger.info(f"Пользователь {user_id} успешно зарегестрировался")


    await bot.send_message(
        user_id=user_id,
        text=(
            "Привет! Можешь задавать любые вопросы по истории и политической ситуации."
            "Я задоминирую❗"
        )
    )


@dp.message_created(F.message.body.text)
async def handle_message(event: MessageCreated):
    text = event.message.body.text
    if text.startswith('/'):
        return

    user_id = event.message.sender.user_id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    logger.info(f"Пользователь {user_id} отправил сообщение: {text[:10]}")

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    # if not session_user:
    #     logger.warning(f"У пользователя {user_id} не найдена сессия")
    #     await bot.send_message(
    #         user_id=user_id,
    #         text="Данные не найдены.\n\nИспользуйте команду /new"
    #     )

    # elif not await MaxService.can_send_message(user_id):
    #     logger.warning(f"У пользователя {user_id} не активирована подписка - нет возможности писать")
    #     await bot.send_message(
    #         user_id=user_id,
    #         text="🔒 Ваша подписка не активна.\nПожалуйста, оплатите доступ в /sub"
    #     )

    # else:
    selected_topic = "Мировоззрение"
    index_id = THEMES_INDEXES.get(selected_topic)
    history = await MaxService.get_history(user_id, "MAX_Dominant",  limit=200)
    # noinspection PyTypeChecker
    answer = ask_ai_with_index(index_id, text, selected_topic, history)

    if answer:
        await MaxService.add_message(user_id, session_user.id, "user", text, "MAX_Dominant")
        await MaxService.add_message(user_id, session_user.id, "assistant", answer, "MAX_Dominant")
        await bot.send_message(user_id=user_id, text=answer)
        logger.info(f"Пользователь успешно получил ответ от ассистента")
    else:
        logger.error(f"Пользователь {user_id} не получил ответ")
        await bot.send_message(
            user_id=user_id,
            text="⚠️ Не удалось получить ответ. Попробуйте позже."
        )

@dp.message_created(F.message.body.attachments)
async def handle_voice_message(event: MessageCreated):
    user_id = event.message.sender.user_id
    user = await MaxService.get_user(user_id)
    session_user = await MaxService.get_session(user_id)

    logger.info(f"Пользователь {user_id} отправил голосовое сообщение")

    await MaxService.update_user_state(user_id, UserState.ACTIVE_SESSION)

    # if not session_user:
    #     logger.warning(f"У пользователя {user_id} не найдена сессия")
    #     await bot.send_message(
    #         user_id=user_id,
    #         text="Данные не найдены.\n\nИспользуйте команду /new"
    #     )

    # elif not await MaxService.can_send_message(user_id):
    #     logger.warning(f"У пользователя {user_id} не активирована подписка - нет возможности писать")
    #     await bot.send_message(
    #         user_id=user_id,
    #         text="🔒 Ваша подписка не активна.\nПожалуйста, оплатите доступ в /sub"
    #     )

    # else:
    selected_topic = "Мировоззрение"
    index_id = THEMES_INDEXES.get(selected_topic)
    history = await MaxService.get_history(user_id, "MAX_Dominant", limit=200)


    audio_attachment = None
    # noinspection PyTypeChecker
    for att in event.message.body.attachments:
        if att.type == "audio":
            audio_attachment = att
            break
    if not audio_attachment:
        return
    audio_url = audio_attachment.payload.url
    print(audio_url)

    try:
        headers = {"User-Agent": "MAX/1.0", "Referer": "https://max.ru/"}

        async with aiohttp.ClientSession() as session_audio:
            async with session_audio.get(audio_url, headers=headers) as resp:
                audio_data = await resp.read()

        mime = magic.from_buffer(audio_data, mime=True)
        if mime != 'audio/ogg':
            process = subprocess.run(
                ['ffmpeg', '-i', 'pipe:0', '-c:a', 'libopus', '-ar', '48000', '-b:a', '64k', '-f', 'ogg', 'pipe:1'],
                input=audio_data,
                capture_output=True
            )
            if process.returncode != 0:
                raise Exception(process.stderr.decode())
            audio_data = process.stdout

        s3_url = await upload_to_s3(audio_data)

        recognized_text = AudioService.recognize_from_s3(s3_url, settings.YC_API_KEY)

        answer = ask_ai_with_index(index_id, recognized_text, selected_topic, history)

        if answer:
            # if user.memory_mode != MemoryMode.none:
            await MaxService.add_message(user_id, session_user.id, "user", recognized_text, "MAX_Dominant")
            await MaxService.add_message(user_id, session_user.id, "assistant", answer, "MAX_Dominant")
            await bot.send_message(user_id=user_id, text=answer)
            logger.info(f"Пользователь {user_id} успешно получил ответ от ассистента")
        else:
            logger.error(f"Пользователь {user_id} не получил ответ")
            await bot.send_message(
                user_id=user_id,
                text="⚠️ Не удалось получить ответ. Попробуйте позже."
            )

    except Exception as e:
        logger.exception(f"Ошибка обработки голосового сообщения от пользователя {user_id}, ошибка: {e}")
        await bot.send_message(user_id=user_id, text="⚠️ Ошибка обработки голосового. Попробуйте текстом.")

async def main():
    webhook_url = "https://bot.nepovinnyh.ru/webhook2"
    webhook_secret = settings.SECRET_WEBHOOK_KEY

    # Регистрируем новую на поддомен
    await bot.subscribe_webhook(url=webhook_url, secret=webhook_secret)

    await dp.handle_webhook(
        bot=bot,
        host='0.0.0.0',
        port=8082,
        secret=webhook_secret,
        path='/webhook2'
    )

if __name__ == '__main__':
    logger.info("Бот успешно запущен")
    asyncio.run(main())
