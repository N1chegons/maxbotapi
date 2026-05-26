import asyncio
import logging
import boto3
import uuid
from botocore.config import Config

from src.config import settings
from src.logger_config import setup_logger
from src.max.repository import MaxService

# Создаём логгер для утилит
logger = setup_logger("utils", "max", "utils.log")

s3_config = Config(
    region_name='ru-central1',
    signature_version='s3v4',
    s3={'addressing_style': 'virtual'}
)


def get_s3_client():
    logger.debug("Создание клиента S3")
    return boto3.client(
        's3',
        endpoint_url='https://storage.yandexcloud.net',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=s3_config
    )


async def upload_to_s3(audio_data: bytes) -> str:
    file_key = f"voice_{uuid.uuid4().hex}.ogg"
    logger.info(f"Загрузка аудио в S3: {file_key}, размер: {len(audio_data)} байт")

    s3 = get_s3_client()

    try:
        s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=file_key,
            Body=audio_data,
            ContentType='audio/ogg'
        )

        file_url = f"https://storage.yandexcloud.net/{settings.S3_BUCKET_NAME}/{file_key}"
        logger.info(f"Аудио успешно загружено в S3: {file_url}")
        return file_url

    except Exception as e:
        logger.error(f"Ошибка при загрузке аудио в S3: {e}")
        raise


async def broadcast_to_all(message_text: str):
    """
    Отправляет сообщение всем пользователям из базы данных.
    Запуск в консоли PyCharm: from tg_bot import broadcast_to_all; asyncio.run(broadcast_to_all("Твой текст"))
    """
    # Получаем всех пользователей из БД
    users = await MaxService.get_users()  # Нужно добавить этот метод

    if not users:
        print("Нет пользователей для рассылки")
        return

    print(f"Начинаю рассылку для {len(users)} пользователей...")

    success = 0
    fail = 0

    for user in users:
        try:
            user_id = user.user_id
            await bot.send_message(
                user_id=user_id,
                text=message_text,
            )
            success += 1
            await asyncio.sleep(0.05)  # Пауза чтобы не заблокировали
            print(f"✅ Отправлено {success}/{len(users)}")
        except Exception as e:
            fail += 1
            print(f"❌ Ошибка {user.user_id}: {e}")

    print(f"\nГотово! Успешно: {success}, Ошибок: {fail}")

asyncio.run(broadcast_to_all("Ребята, спасибо за тест: нашли баг в связи с Точкой. Заходите завтра в бот, получите доступ. С четверга придётся снова 14 рублей платить"))
from src.max.bot import bot
