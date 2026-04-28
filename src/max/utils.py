import boto3
import uuid
from botocore.config import Config
from maxapi import Bot
from maxapi.types import InputMedia
from maxapi.types.attachments import Video
from maxapi.types.attachments.video import VideoThumbnail

from src.config import settings

s3_config = Config(
    region_name='ru-central1',
    signature_version='s3v4',
    s3={'addressing_style': 'virtual'}
)

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url='https://storage.yandexcloud.net',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=s3_config
    )

async def upload_to_s3(audio_data: bytes) -> str:
    file_key = f"voice_{uuid.uuid4().hex}.ogg"
    s3 = get_s3_client()
    s3.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=file_key,
        Body=audio_data,
        ContentType='audio/ogg'
    )
    return f"https://storage.yandexcloud.net/{settings.S3_BUCKET_NAME}/{file_key}"

