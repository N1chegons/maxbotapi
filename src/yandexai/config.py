from openai import OpenAI

from src.config import settings

yandex_client = OpenAI(
    base_url="https://ai.api.cloud.yandex.net/v1",
    api_key=settings.YC_API_KEY,
    project=settings.YC_FOLDER_ID
)

THEMES_INDEXES = {
        "Мировоззрение": settings.SEARCH_INDEX_2027
    }
THEMES_DESCRIPTIONS = {
        "Мировоззрение": "актуальные взгляды и позиции эксперта"
    }