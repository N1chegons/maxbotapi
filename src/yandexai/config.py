from openai import OpenAI

from src.config import settings

client = OpenAI(
    base_url="https://ai.api.cloud.yandex.net/v1",
    api_key=settings.YC_API_KEY,
    project=settings.YC_FOLDER_ID
)

THEMES_INDEXES = {
        "Путь": settings.SEARCH_INDEX_1987,
        "Консультации": settings.SEARCH_INDEX_2010,
        "Теория": settings.SEARCH_INDEX_2015,
        "Мировоззрение": settings.SEARCH_INDEX_2027
    }
THEMES_DESCRIPTIONS = {
        "Путь": "личная история эксперта, опыт, примеры, аналогии",
        "Консультации": "диалоговая поддержка, поиск решений, работа с запросом",
        "Теория": "профессиональные концепции и подходы",
        "Мировоззрение": "актуальные взгляды и позиции эксперта"
    }