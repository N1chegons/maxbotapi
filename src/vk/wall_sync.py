import json
import requests
import random
import re
from typing import List, Optional
from src.config import settings
from src.logger_config import setup_logger

logger = setup_logger('wall_sync', 'vk', 'wall_sync.log')


class WallSyncService:
    def __init__(self, group_id: int = 186451829, cache_file: str = "/home/bots/maxbotapi/wall_cache.json"):
        self.token = settings.VK_ACCESS_TOKEN
        self.group_id = group_id
        self.cache_file = cache_file
        self.api_version = "5.199"

    def fetch_current_posts(self, count: int = 100) -> List[int]:
        """Получает актуальный список ID постов со стены через API"""
        url = "https://api.vk.com/method/wall.get"
        params = {
            "owner_id": -self.group_id,
            "count": count,
            "access_token": self.token,
            "v": self.api_version
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if "error" in data:
                logger.error(f"Ошибка API ВК при получении стены: {data['error']['error_msg']}")
                return []

            posts = data["response"]["items"]
            return [post["id"] for post in posts]

        except Exception as e:
            logger.error(f"Ошибка запроса к ВК API: {e}")
            return []

    def update_cache(self):
        """Синхронизирует кэш: добавляет новые посты, удаляет пропавшие"""
        current_posts = self.fetch_current_posts()
        if not current_posts:
            logger.warning("Не удалось получить посты. Кэш не обновлен.")
            return

        # Читаем старый кэш
        old_posts = []
        try:
            with open(self.cache_file, "r") as f:
                old_posts = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        # Diff-логика
        added = list(set(current_posts) - set(old_posts))
        removed = list(set(old_posts) - set(current_posts))

        if added:
            logger.info(f"➕ Новые посты: {added}")
        if removed:
            logger.info(f"➖ Удаленные посты: {removed}")

        # Сохраняем новый кэш
        with open(self.cache_file, "w") as f:
            json.dump(current_posts, f)

        logger.info(f"✅ Кэш синхронизирован. Всего актуальных постов: {len(current_posts)}")

    def get_random_post(self) -> Optional[dict]:
        """Возвращает случайный пост из актуального кэша"""
        try:
            with open(self.cache_file, "r") as f:
                posts = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Кэш стены пуст. Запустите update_cache()")
            return None

        if not posts:
            return None

        post_id = random.choice(posts)
        post_url = f"https://vk.ru/wall-{self.group_id}_{post_id}"

        # Опционально: можно добавить сюда логику парсинга красивой ссылки (@socnep.biblio),
        # если она нужна. Но пока возвращаем прямую ссылку.

        return {
            "id": post_id,
            "url": post_url,
            "description": "📖 Интересная статья"
        }