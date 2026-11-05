import json
import os
from datetime import datetime, timedelta
from src.logger_config import setup_logger

logger = setup_logger('weekly_cache', 'vk', 'weekly_cache.log')


class WeeklyCache:
    def __init__(self, cache_file: str = "weekly_usage.json", days: int = 7):
        self.cache_file = cache_file
        self.days = days
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.data, f, indent=2)

    def _cleanup(self):
        """Удаляет записи старше N дней"""
        now = datetime.now()
        expired = []
        for item_id, date_str in self.data.items():
            usage_date = datetime.fromisoformat(date_str)
            if now - usage_date > timedelta(days=self.days):
                expired.append(item_id)

        for item in expired:
            del self.data[item]

        if expired:
            logger.info(f"🧹 Очищено {len(expired)} старых записей из кэша.")
            self._save()

    def is_used(self, item_id: str) -> bool:
        """Проверяет, использовался ли элемент за последние N дней"""
        self._cleanup()
        return str(item_id) in self.data

    def mark_used(self, item_id: str):
        """Отмечает элемент как использованный"""
        self.data[str(item_id)] = datetime.now().isoformat()
        self._save()

    def get_oldest_and_remove(self) -> str | None:
        """Возвращает ID самой старой записи и удаляет её из кэша (FIFO)"""
        if not self.data:
            return None

        # Сортируем по дате (по возрастанию) и берем первый
        oldest_item = min(self.data.items(), key=lambda x: x[1])
        item_id = oldest_item[0]

        # Удаляем его из кэша, чтобы можно было использовать снова
        del self.data[item_id]
        self._save()

        logger.info(f"🔄 Кэш заполнен. Берем самый старый элемент: {item_id} и удаляем его из кэша.")
        return item_id