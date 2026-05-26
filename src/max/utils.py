import boto3
import uuid
from botocore.config import Config

from src.config import settings
from src.logger_config import setup_logger

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