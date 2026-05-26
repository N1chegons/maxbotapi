import json
from typing import Optional, Dict, List, Tuple, Any
import random
import subprocess
from urllib.parse import quote

import requests
from pathlib import Path
from aiofiles import os
from src.logger_config import setup_logger
from src.max.utils import get_s3_client
from src.config import settings
import asyncio
import re
from playwright.async_api import async_playwright

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)


logger = setup_logger('vk_publisher', 'vk_publisher', 'vk_publisher.log')


class VkIntegrationNew:
    def __init__(self):
        self.channel_id = "-70970272101791"
        self.bot_token = settings.MAX_BOT_TOKEN
        self.token = settings.VK_ACCESS_TOKEN
        self.group_id = settings.VK_GROUP_ID

        self.current_video_index = 0
        self.video_links = []
        self.clips_file = "clips_links.txt"

        self.playlist = [
            "https://vkvideo.ru/playlist/420142_35",
            "https://vkvideo.ru/playlist/420142_34",
            "https://vkvideo.ru/playlist/420142_28",
            "https://vkvideo.ru/playlist/420142_26",
            "https://vkvideo.ru/playlist/420142_22",
            "https://vkvideo.ru/playlist/420142_20",
            "https://vkvideo.ru/playlist/420142_17",
            "https://vkvideo.ru/playlist/420142_15",
            "https://vkvideo.ru/playlist/420142_13",
            "https://vkvideo.ru/playlist/420142_12"
        ]

        self.scheduled_playlists = {
            "Работаев": "https://vkvideo.ru/playlist/-141287828_2",
            "Неповинных": "https://vkvideo.ru/playlist/-141287828_3",
            "Прохоров": "https://vkvideo.ru/playlist/-141287828_4"
        }

    def get_video_links_from_playlist(self, playlist_url: str) -> list:
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--flat-playlist",
                    "--print", "webpage_url",
                    playlist_url
                ],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                print(f"Ошибка yt-dlp: {result.stderr}")
                return []
            links = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return links
        except Exception as e:
            print(f"Ошибка: {e}")
            return []

    def get_all_video_links(self) -> list:
        all_links = []
        for playlist_url in self.playlist:
            print(f"Обработка {playlist_url}...")
            links = self.get_video_links_from_playlist(playlist_url)
            all_links.extend(links)
            print(f"  Найдено {len(links)} видео")
        print(f"\n📊 ИТОГО: {len(all_links)} видео")
        return all_links

    def send_to_channel(self, text: str):
        url = f"https://platform-api.max.ru/messages?chat_id={self.channel_id}"
        headers = {
            "Authorization": f"{self.bot_token}",
            "Content-Type": "application/json"
        }
        payload = {"text": text}
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()

    def send_random_video(self):
        try:
            if not self.video_links:
                with open("video_links.txt", "r") as f:
                    self.video_links = f.read().splitlines()
                self.video_links = [link.replace('vk.com', 'vk.ru') for link in self.video_links]
                random.shuffle(self.video_links)
            if not self.video_links:
                return None
            video_url = self.video_links[self.current_video_index]
            self.current_video_index = (self.current_video_index + 1) % len(self.video_links)
            if self.current_video_index == 0:
                random.shuffle(self.video_links)
            message = f"🎬\n\n{video_url}"
            self.send_to_channel(message)
            return video_url
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

    async def update_clips(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://vk.ru/clips/plangod", timeout=60000)
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(2)
            links = await page.evaluate('''() => {
                const items = document.querySelectorAll('a[href*="clip-"]');
                const result = [];
                items.forEach(a => {
                    let href = a.getAttribute('href');
                    if (href && href.includes('clip-') && !href.includes('search')) {
                        result.push(href);
                    }
                });
                return [...new Set(result)];
            }''')
            await browser.close()
            clean_links = []
            for link in links:
                match = re.search(r'(clip-\d+_\d+)', link)
                if match:
                    clean_links.append(f"https://vk.com/{match.group(1)}")
            if clean_links:
                with open(self.clips_file, "w") as f:
                    f.write("\n".join(clean_links))
                print(f"✅ Сохранено {len(clean_links)} клипов")
            else:
                print("❌ Клипы не найдены")

    def send_random_clip(self):
        try:
            # noinspection PySuspiciousBooleanCondition
            if not os.path.exists(self.clips_file):
                print("❌ Файл с клипами не найден")
                return
            with open(self.clips_file, "r") as f:
                clips = f.read().splitlines()
            if not clips:
                print("❌ Нет клипов в файле")
                return
            clip_url = random.choice(clips)
            clip_url = clip_url.replace('vk.com', 'vk.ru')
            url = f"https://platform-api.max.ru/messages?chat_id={self.channel_id}"
            headers = {"Authorization": self.bot_token, "Content-Type": "application/json"}
            payload = {"text": f"🎬\n\n{clip_url}"}
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            if response.status_code == 200:
                print(f"✅ Отправлен клип")
            else:
                print(f"❌ Ошибка отправки: {response.status_code}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    def get_random_video_from_playlist(self, playlist_url: str) -> Any | None:
        """Возвращает случайную ссылку на видео из плейлиста"""
        links = self.get_video_links_from_playlist(playlist_url)
        if not links:
            return None
        return random.choice(links)

    def post_scheduled_video(self, playlist_name: str):
        """Публикует случайное видео из заданного плейлиста в канал"""
        playlist_url = self.scheduled_playlists.get(playlist_name)
        if not playlist_url:
            print(f"❌ Плейлист {playlist_name} не найден")
            return

        video_url = self.get_random_video_from_playlist(playlist_url)
        if not video_url:
            print(f"❌ Нет видео в плейлисте {playlist_name}")
            return

        message = f"🎬\n{video_url}"
        self.send_to_channel(message)
        print(f"✅ Отправлено видео из плейлиста {playlist_name}")


# noinspection PyTypeChecker
class VkIntegration:
    def __init__(self):
        self.channel_id = settings.MAX_CHANNEL_ID
        self.bot_token = settings.MAX_BOT_TOKEN

        # S3 клиент для PDF
        self.s3 = get_s3_client()

        # Бакеты для PDF
        self.pdf_buckets = {
            "mod": "mod.nepovinnyh.ru",
            "fa": "fa.nepovinnyh.ru",
            "zh": "zh.nepovinnyh.ru",
            "soc": "soc.nepovinnyh.ru",
            "pt": "pt.nepovinnyh.ru",
        }

        # Префиксы для видео (заголовки)
        self.video_prefixes = {
            "Здоровье": "🏥 Немного о здоровье",
            "Логистика": "🚂 Прокатимся по России",
            "Сила": "💪 А ты знал?",
            "Специалисты": "🎯 Специализация важна",
            "Машиностроение": "⚙️ Машиностроение России",
            "Педагогика": "📚 А ты знал?",
            "Питание": "🍎 А ты знал?",
            "Строительство": "🏗️ Строительство России",
        }

        # Префиксы для PDF
        self.pdf_prefixes = {
            "mod": "📘 Четвёртая модернизация России",
            "fa": "🇮🇷 Передай привет иранскому другу",
            "zh": "🇨🇳 Передай привет китайскому другу",
            "soc": "📖 Социология Неповинных",
            "pt": "🇧🇷 Есть друг из Анголы или Бразилии?",
        }

        # Плейлисты для видео (тема → ссылка на плейлист VK Video)
        self.video_playlists = {
            "Машиностроение": "https://vkvideo.ru/playlist/-216257056_1",
            "Педагогика": "https://vkvideo.ru/playlist/-216257056_2",
            "Питание": "https://vkvideo.ru/playlist/-216257056_3",
            "Строительство": "https://vkvideo.ru/playlist/-216257056_4",
            "Логистика": "https://vkvideo.ru/playlist/-216257056_5",
            "Специалисты": "https://vkvideo.ru/playlist/-216257056_6",
            "Сила": "https://vkvideo.ru/playlist/-216257056_7",
            "Здоровье": "https://vkvideo.ru/playlist/-216257056_8",
        }

        # Очерёдность публикаций
        self.order: List[Tuple[str, str]] = [
            ("playlist", "Здоровье"),
            ("playlist", "Педагогика"),
            ("pdf", "mod"),
            ("playlist", "Машиностроение"),
            ("playlist", "Строительство"),
            ("pdf", "fa"),
            ("playlist", "Сила"),
            ("playlist", "Специалисты"),
            ("playlist", "Логистика"),  # Статьи убрал, так как нет токена
            ("playlist", "Питание"),
            ("pdf", "zh"),
            ("playlist", "Сила"),
            ("playlist", "Специалисты"),
            ("pdf", "soc"),
            ("playlist", "Здоровье"),
            ("playlist", "Педагогика"),
            ("pdf", "pt"),
        ]

        # Файл для сохранения текущего индекса
        self.index_file = "/home/psylogic/current_index.txt"

        # Кэш для ссылок видео (чтобы не парсить каждый раз)
        self.video_cache_file = "/home/psylogic/video_cache.json"
        self.video_cache = self._load_video_cache()

    def _load_video_cache(self) -> Dict:
        """Загружает кэш ссылок видео из JSON файла"""
        try:
            with open(self.video_cache_file, "r") as f:
                return json.load(f)
        except:
            return {}

    def _save_video_cache(self):
        """Сохраняет кэш ссылок видео в JSON файл"""
        with open(self.video_cache_file, "w") as f:
            json.dump(self.video_cache, f, indent=2)

    def get_video_links_from_playlist(self, playlist_url: str) -> list:
        """Получает все ссылки на видео из плейлиста через yt-dlp"""
        try:
            # Пробуем взять из кэша
            if playlist_url in self.video_cache:
                logger.info(f"Загружено из кэша: {playlist_url} -> {len(self.video_cache[playlist_url])} видео")
                return self.video_cache[playlist_url]

            logger.info(f"Парсинг плейлиста через yt-dlp: {playlist_url}")

            result = subprocess.run(
                [
                    "yt-dlp",
                    "--flat-playlist",
                    "--print", "webpage_url",
                    playlist_url
                ],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                logger.error(f"Ошибка yt-dlp: {result.stderr}")
                return []

            links = [line.strip() for line in result.stdout.splitlines() if line.strip()]

            # Заменяем vk.com на vkvideo.ru для единообразия
            links = [link.replace('vk.com', 'vkvideo.ru') for link in links]

            logger.info(f"Найдено {len(links)} видео в плейлисте")

            # Сохраняем в кэш
            self.video_cache[playlist_url] = links
            self._save_video_cache()

            return links

        except subprocess.TimeoutExpired:
            logger.error(f"Таймаут при парсинге {playlist_url}")
            return []
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return []

    def get_random_video_from_playlist(self, playlist_url: str) -> Optional[str]:
        """Возвращает случайную ссылку на видео из плейлиста"""
        links = self.get_video_links_from_playlist(playlist_url)
        if not links:
            return None
        return random.choice(links)

    # ========== РАБОТА С PDF ==========
    async def get_pdf_from_s3(self, prefix: str) -> Optional[Dict]:
        """Получить случайный PDF из соответствующего бакета"""
        try:
            bucket = self.pdf_buckets.get(prefix)
            if not bucket:
                logger.error(f"Неизвестный префикс: {prefix}")
                return None

            has_description = prefix in ["mod", "soc"]

            response = self.s3.list_objects_v2(Bucket=bucket, Prefix="")

            if 'Contents' not in response:
                logger.warning(f"Нет файлов в бакете {bucket}")
                return None

            pdf_files = []
            for obj in response['Contents']:
                key = obj['Key']
                if key.lower().endswith('.pdf'):
                    pdf_files.append(key)

            if not pdf_files:
                logger.warning(f"Нет PDF в бакете {bucket}")
                return None

            pdf_key = random.choice(pdf_files)

            # Кодируем русские буквы и пробелы в URL
            encoded_key = quote(pdf_key, safe='')
            pdf_url = f"https://storage.yandexcloud.net/{bucket}/{encoded_key}"

            description = None
            if has_description:
                txt_key = pdf_key.replace('.pdf', '.txt')
                try:
                    txt_obj = self.s3.get_object(Bucket=bucket, Key=txt_key)
                    txt_content = txt_obj['Body'].read().decode('utf-8')
                    description = txt_content.strip()
                    logger.info(f"Описание загружено для {pdf_key}")
                except Exception as e:
                    logger.debug(f"Нет TXT для {pdf_key}: {e}")

            filename = Path(pdf_key).stem.replace('_', ' ').replace('-', ' ')

            return {
                'url': pdf_url,
                'description': description,
                'filename': filename,
                'key': pdf_key
            }

        except Exception as e:
            logger.error(f"Ошибка получения PDF из S3: {e}")
            return None

    # ========== ОТПРАВКА В КАНАЛ ==========
    def send_to_channel(self, text: str):
        """Отправить сообщение в канал MAX"""
        url = f"https://platform-api.max.ru/messages?chat_id={self.channel_id}"
        headers = {
            "Authorization": f"{self.bot_token}",
            "Content-Type": "application/json"
        }
        payload = {"text": text}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка отправки в канал: {e}")
            raise

    def get_current_index(self) -> int:
        """Получить текущий индекс публикации"""
        try:
            with open(self.index_file, "r") as f:
                return int(f.read().strip())
        except:
            return 0

    def save_current_index(self, index: int):
        """Сохранить текущий индекс"""
        with open(self.index_file, "w") as f:
            f.write(str(index))

    def publish_next(self):
        """Опубликовать следующий контент по расписанию"""
        index = self.get_current_index()
        item_type, item_name = self.order[index % len(self.order)]

        logger.info(f"📢 [{index}] Публикация: {item_type} - {item_name}")

        message = None

        try:
            if item_type == "playlist":
                # Берём случайное видео из плейлиста через yt-dlp
                playlist_url = self.video_playlists.get(item_name)
                if not playlist_url:
                    logger.error(f"Нет плейлиста для {item_name}")
                    return

                video_url = self.get_random_video_from_playlist(playlist_url)
                if not video_url:
                    logger.error(f"Не удалось получить видео из плейлиста {item_name}")
                    return

                prefix = self.video_prefixes.get(item_name, "")
                message = f"{prefix}\n\n🎬 Смотреть: {video_url}"

            elif item_type == "pdf":
                # PDF из S3
                pdf_data = asyncio.run(self.get_pdf_from_s3(item_name))
                if not pdf_data:
                    logger.error(f"Нет PDF для {item_name}")
                    return

                prefix = self.pdf_prefixes.get(item_name, "📄 Материал")
                description = pdf_data.get('description')

                if description:
                    message = f"{prefix}\n\n{description}\n\n📄 Читать: {pdf_data['url']}"
                else:
                    message = f"{prefix}\n\n{pdf_data['filename']}\n\n📄 Читать: {pdf_data['url']}"

            if message:
                if len(message) > 4096:
                    message = message[:4093] + "..."

                self.send_to_channel(message)
                logger.info(f"✅ Опубликовано: {item_type} - {item_name}")

                # Сохраняем следующий индекс
                new_index = (index + 1) % len(self.order)
                self.save_current_index(new_index)
                logger.info(f"📌 Следующий индекс: {new_index}")

        except Exception as e:
            logger.error(f"❌ Ошибка публикации: {e}")


def publish_once():
    """Опубликовать один раз (для теста)"""
    publisher = VkIntegration()
    publisher.publish_next()


publish_once()