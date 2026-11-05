import json
import requests
import random
import re
from typing import List, Optional
from src.config import settings
from src.logger_config import setup_logger
from src.vk.weekly_cache import WeeklyCache

logger = setup_logger('wall_sync', 'vk', 'wall_sync.log')


class WallSyncService:
    def __init__(self, group_id: int = 186451829, cache_file: str = "/home/bots/maxbotapi/wall_cache.json"):
        self.token = settings.VK_ACCESS_TOKEN
        self.group_id = group_id
        self.cache_file = cache_file
        self.api_version = "5.199"
        # Инициализируем недельный кэш для статей
        self.weekly_cache = WeeklyCache(cache_file="/home/bots/maxbotapi/weekly_articles.json")

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

        old_posts = []
        try:
            with open(self.cache_file, "r") as f:
                old_posts = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        added = list(set(current_posts) - set(old_posts))
        removed = list(set(old_posts) - set(current_posts))

        if added:
            logger.info(f"➕ Новые посты: {added}")
        if removed:
            logger.info(f"➖ Удаленные посты: {removed}")

        with open(self.cache_file, "w") as f:
            json.dump(current_posts, f)

        logger.info(f"✅ Кэш синхронизирован. Всего актуальных постов: {len(current_posts)}")

    def get_random_post(self) -> Optional[dict]:
        """Возвращает случайный пост из актуального кэша с учетом недельного кэша"""
        try:
            with open(self.cache_file, "r") as f:
                posts = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Кэш стены пуст. Запустите update_cache()")
            return None

        if not posts:
            return None

        random.shuffle(posts)

        # 1. Ищем новый пост (которого нет в недельном кэше)
        for post_id in posts:
            if not self.weekly_cache.is_used(post_id):
                post_url = f"https://vk.ru/wall-{self.group_id}_{post_id}"
                self.weekly_cache.mark_used(post_id)
                return {"id": post_id, "url": post_url, "description": "📖 Интересная статья"}

        # 2. Если все посты использованы, берем самый старый (FIFO)
        logger.warning("Все статьи со стены использованы. Применяем FIFO.")
        oldest_post_id = self.weekly_cache.get_oldest_and_remove()

        if oldest_post_id:
            self.weekly_cache.mark_used(oldest_post_id)
            post_url = f"https://vk.ru/wall-{self.group_id}_{oldest_post_id}"
            return {"id": int(oldest_post_id), "url": post_url, "description": "📖 Интересная статья"}

        # 3. Крайний случай (если кэш вообще пуст)
        fallback_id = random.choice(posts)
        return {"id": fallback_id, "url": f"https://vk.ru/wall-{self.group_id}_{fallback_id}",
                "description": "📖 Интересная статья"}