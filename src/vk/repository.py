import json
from typing import Optional, Dict, Any
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

class VkIntegration:
    def __init__(self):
        self.channel_id = settings.MAX_CHANNEL_ID
        self.bot_token = settings.MAX_BOT_TOKEN

        # S3 клиент
        self.s3 = get_s3_client()

        # Бакеты для PDF
        self.pdf_buckets = {
            "mod": "mod.nepovinnyh.ru",
            "fa": "fa.nepovinnyh.ru",
            "zh": "zh.nepovinnyh.ru",
            "soc": "soc.nepovinnyh.ru",
            "pt": "pt.nepovinnyh.ru",
        }

        # Префиксы для PDF (заголовки)
        self.pdf_prefixes = {
            "mod": "📘 Четвёртая модернизация России",
            "fa": "🇮🇷 Передай привет иранскому другу",
            "zh": "🇨🇳 Передай привет китайскому другу",
            "soc": "📖 Социология Неповинных",
            "pt": "🇧🇷 Есть друг из Анголы или Бразилии?",
        }

        # Префиксы для видео (заголовки)
        self.video_prefixes = {
            "Здоровье": "🏥 Немного о здоровье",
            "Машиностроение": "⚙️ Машиностроение России",
            "Педагогика": "📚 А ты знал?",
            "Питание": "🍎 А ты знал?",
            "Строительство": "🏗️ Строительство России",
            "Логистика": "🚂 Прокатимся по России",
            "Сила": "💪 А ты знал?",
            "Специалисты": "🎯 Специализация важна",
        }

        # Первый лист (тематические плейлисты)
        self.playlist_type1 = [
            "Здоровье",
            "Машиностроение",
            "Педагогика",
            "Питание",
            "Строительство",
            "Логистика"
        ]

        # Второй лист (общие плейлисты)
        self.playlist_type2 = [
            "Сила",
            "Специалисты"
        ]

        # Ссылки на плейлисты VK
        self.playlist_urls = {
            "Здоровье": "https://vkvideo.ru/playlist/-216257056_8",
            "Машиностроение": "https://vkvideo.ru/playlist/-216257056_1",
            "Педагогика": "https://vkvideo.ru/playlist/-216257056_2",
            "Питание": "https://vkvideo.ru/playlist/-216257056_3",
            "Строительство": "https://vkvideo.ru/playlist/-216257056_4",
            "Логистика": "https://vkvideo.ru/playlist/-216257056_5",
            "Сила": "https://vkvideo.ru/playlist/-216257056_7",
            "Специалисты": "https://vkvideo.ru/playlist/-216257056_6",
        }

        # Файлы для хранения состояния (чтобы помнить, что публиковать по кругу)
        self.state_files = {
            "type1_index": "/home/psylogic/type1_index.txt",
            "type2_index": "/home/psylogic/type2_index.txt",
        }

        # Кэш для ссылок видео
        self.video_cache_file = "/home/psylogic/video_cache.json"
        self.video_cache = self._load_video_cache()

    def _load_video_cache(self) -> Dict:
        try:
            with open(self.video_cache_file, "r") as f:
                return json.load(f)
        except:
            return {}

    def _save_video_cache(self):
        with open(self.video_cache_file, "w") as f:
            json.dump(self.video_cache, f, indent=2)

    def _get_next_index(self, file_path: str, max_index: int) -> int:
        """Получить следующий индекс по кругу"""
        try:
            with open(file_path, "r") as f:
                index = int(f.read().strip())
        except:
            index = 0

        next_index = (index + 1) % max_index

        with open(file_path, "w") as f:
            f.write(str(next_index))

        return index  # возвращаем текущий индекс (то, что надо публиковать)

    def get_next_playlist_type1(self) -> str:
        """Получить следующую тему из первого листа"""
        index = self._get_next_index(self.state_files["type1_index"], len(self.playlist_type1))
        return self.playlist_type1[index]

    def get_next_playlist_type2(self) -> str:
        """Получить следующую тему из второго листа"""
        index = self._get_next_index(self.state_files["type2_index"], len(self.playlist_type2))
        return self.playlist_type2[index]

    def get_video_links_from_playlist(self, playlist_url: str) -> list:
        """Получить все ссылки на видео из плейлиста через yt-dlp"""
        if playlist_url in self.video_cache:
            logger.info(f"Из кэша: {len(self.video_cache[playlist_url])} видео")
            return self.video_cache[playlist_url]

        try:
            result = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--print", "webpage_url", playlist_url],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                logger.error(f"Ошибка yt-dlp: {result.stderr}")
                return []

            links = [line.strip().replace('vk.com', 'vkvideo.ru') for line in result.stdout.splitlines() if
                     line.strip()]
            self.video_cache[playlist_url] = links
            self._save_video_cache()
            logger.info(f"Найдено {len(links)} видео в плейлисте")
            return links
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return []

    def get_random_video_from_playlist(self, playlist_name: str) -> Optional[str]:
        """Возвращает случайную ссылку на видео из плейлиста"""
        playlist_url = self.playlist_urls.get(playlist_name)
        if not playlist_url:
            return None
        links = self.get_video_links_from_playlist(playlist_url)
        if not links:
            return None
        return random.choice(links)

    def get_video_description(self, video_url: str) -> str:
        """Получить описание видео через yt-dlp"""
        try:
            result = subprocess.run(
                ["yt-dlp", "--get-description", video_url],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return ""
            desc = result.stdout.strip()
            if len(desc) > 800:
                desc = desc[:797] + "..."
            return desc
        except:
            return ""

    def get_pdf_from_s3(self, prefix: str) -> Optional[Dict]:
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
            logger.info(f"Выбран PDF: {pdf_key}")

            # Кодируем URL
            encoded_key = quote(pdf_key, safe='')
            pdf_url = f"https://storage.yandexcloud.net/{bucket}/{encoded_key}"

            # Ищем описание
            description = None
            if has_description:
                txt_key = pdf_key.replace('.pdf', '.txt')
                logger.debug(f"Ищем описание: {txt_key}")

                try:
                    txt_obj = self.s3.get_object(Bucket=bucket, Key=txt_key)
                    txt_content = txt_obj['Body'].read().decode('utf-8')
                    description = txt_content.strip()
                    logger.info(f"Описание загружено для {pdf_key}, длина {len(description)} символов")
                except Exception as e:
                    logger.warning(f"Не удалось загрузить txt для {pdf_key}: {e}")

            filename = Path(pdf_key).stem.replace('_', ' ').replace('-', ' ')

            # Если описания нет — используем имя файла
            if not description:
                description = filename
                logger.info(f"Использую имя файла как описание: {filename}")

            return {
                'url': pdf_url,
                'description': description,
                'filename': filename
            }

        except Exception as e:
            logger.error(f"Ошибка получения PDF из S3: {e}")
            return None

    def get_random_article(self) -> Optional[Dict]:
        """Получить случайную статью из VK (через yt-dlp парсинг)"""
        # Альтернатива: парсим статьи через requests + BeautifulSoup
        # Пока вернём заглушку, но можно сделать полноценный парсинг
        try:
            # Пример ссылки на книгу
            article_url = "https://vk.ru/@-186451829-duet-02"
            return {
                'url': article_url,
                'description': "Дуэт — это книга о взаимодействии и сотрудничестве."
            }
        except:
            return None

    def send_to_channel(self, text: str):
        """Отправить в канал MAX"""
        if len(text) > 4096:
            text = text[:4093] + "..."

        url = f"https://platform-api.max.ru/messages?chat_id={self.channel_id}"
        headers = {"Authorization": f"{self.bot_token}", "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json={"text": text}, timeout=30)
        response.raise_for_status()
        return response.json()

    def publish_video(self, playlist_name: str):
        """Опубликовать случайное видео из плейлиста"""
        video_url = self.get_random_video_from_playlist(playlist_name)
        if not video_url:
            logger.error(f"Нет видео для {playlist_name}")
            return

        description = self.get_video_description(video_url)
        prefix = self.video_prefixes.get(playlist_name, "")

        if description:
            message = f"{prefix}\n\n{description}\n\n🎬 Смотреть: {video_url}"
        else:
            message = f"{prefix}\n\n🎬 Смотреть: {video_url}"

        self.send_to_channel(message)
        logger.info(f"Опубликовано видео: {playlist_name}")

    def publish_pdf(self, pdf_prefix: str):
        """Опубликовать PDF"""
        pdf_data = self.get_pdf_from_s3(pdf_prefix)
        if not pdf_data:
            logger.error(f"Нет PDF для {pdf_prefix}")
            return

        prefix = self.pdf_prefixes.get(pdf_prefix, "📄 Материал")
        if pdf_data['description']:
            message = f"{prefix}\n\n{pdf_data['description']}\n\n📄 Читать: {pdf_data['url']}"
        else:
            message = f"{prefix}\n\n{pdf_data['filename']}\n\n📄 Читать: {pdf_data['url']}"

        self.send_to_channel(message)
        logger.info(f"Опубликован PDF: {pdf_prefix}")

    def publish_article(self):
        """Опубликовать книгу/статью"""
        article = self.get_random_article()
        if not article:
            logger.error("Нет статьи")
            return

        message = f"📚 Книга\n\n{article['description']}\n\n📖 Читать: {article['url']}"
        self.send_to_channel(message)
        logger.info("Опубликована статья")


# ========== ЗАПУСК ПО РАСПИСАНИЮ ==========

publisher = VkIntegration()

# Маппинг часа на функцию
schedule_map = {
    9: lambda: publisher.publish_video(publisher.get_next_playlist_type1()),
    10: lambda: publisher.publish_pdf("mod"),
    11: lambda: publisher.publish_video(publisher.get_next_playlist_type1()),
    12: lambda: publisher.publish_video(publisher.get_next_playlist_type1()),
    13: lambda: publisher.publish_pdf("fa"),
    14: lambda: publisher.publish_pdf("zh"),
    15: lambda: publisher.publish_article(),
    16: lambda: publisher.publish_video(publisher.get_next_playlist_type2()),
    17: lambda: publisher.publish_pdf("soc"),
    18: lambda: publisher.publish_video(publisher.get_next_playlist_type2()),
    19: lambda: publisher.publish_pdf("pt"),
    20: lambda: publisher.publish_video(publisher.get_next_playlist_type2()),
}


def run_by_hour(hour: int):
    """Запустить публикацию по часу"""
    if hour in schedule_map:
        logger.info(f"🕐 {hour}:00 - Запуск публикации")
        schedule_map[hour]()
    else:
        logger.debug(f"🕐 {hour}:00 - Нет публикации")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        hour = int(sys.argv[1])
        run_by_hour(hour)