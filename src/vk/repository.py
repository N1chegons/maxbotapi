import random
import time
import subprocess
import json
import requests
import urllib.parse
from pathlib import Path
from ftplib import FTP
import re

from aiofiles import os
from bs4 import BeautifulSoup

from src.config import settings
import asyncio
import re
from playwright.async_api import async_playwright

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

class VkIntegration:
    def __init__(self):
        self.channel_id = settings.MAX_CHANNEL_ID
        self.bot_token = settings.MAX_BOT_TOKEN
        self.token = settings.VK_ACCESS_TOKEN
        self.group_id = settings.VK_GROUP_ID

        self.ftp_host = settings.FTP_HOST
        self.ftp_user = settings.FTP_USER
        self.ftp_pass = settings.FTP_PASS

        self.video_urls = {
            "Машиностроение": "https://vkvideo.ru/video-216257056_456239291?pl=-216257056_1",
            "Педагогика": "https://vkvideo.ru/video-216257056_456240514?pl=-216257056_2",
            "Питание": "https://vkvideo.ru/video-216257056_456240483?pl=-216257056_3",
            "Строительство": "https://vkvideo.ru/video-216257056_456240425?pl=-216257056_4",
            "Логистика": "https://vkvideo.ru/video-216257056_456240485?pl=-216257056_5",
            "Специалисты": "https://vkvideo.ru/video-216257056_456240500?pl=-216257056_6",
            "Сила": "https://vkvideo.ru/video-216257056_456240512?pl=-216257056_7",
            "Здоровье": "https://vkvideo.ru/video-216257056_456240516?pl=-216257056_8",
        }

        self.playlist_prefixes = {
            "Здоровье": "Немного о здоровье 💉",
            "Логистика": "Прокатимся по России 🚂",
            "Сила": "А ты знал ❓",
            "Специалисты": "Специализация важна 🤔",
            "Машиностроение": "Машиностроение России ⚙️",
            "Педагогика": "А ты знал ❓",
            "Питание": "А ты знал ❓",
            "Строительство": "Строительство России 🏗️",
        }

        self.pdf_prefixes = {
            "ru": "Четвёртая модернизация России ⚙️",
            "fa": "Передай привет иранскому другу 🕌",
            "zh": "Передай привет китайскому другу 🇨🇳",
            "sn": "Социология Неповинных 🤔",
            "pt": "Есть друг из Анголы или Бразилии ❓",
        }

        self.order = [
            ("playlist", "Здоровье"),
            ("playlist", "Логистика"),
            ("pdf", "ru"),
            ("playlist", "Сила"),
            ("playlist", "Специалисты"),
            ("pdf", "fa"),
            ("playlist", "Машиностроение"),
            ("playlist", "Педагогика"),
            ("article", None),
            ("playlist", "Сила"),
            ("playlist", "Специалисты"),
            ("pdf", "zh"),
            ("playlist", "Питание"),
            ("playlist", "Строительство"),
            ("pdf", "sn"),
            ("playlist", "Сила"),
            ("playlist", "Специалисты"),
            ("pdf", "pt"),
        ]

        self.index_file = "/home/psylogic/current_index.txt"
        self.pdf_cache_file = "/home/psylogic/pdf_links.json"

    def get_current_index(self):
        try:
            with open(self.index_file, "r") as f:
                return int(f.read().strip())
        except:
            return 0

    def save_current_index(self, index):
        with open(self.index_file, "w") as f:
            f.write(str(index))

    def get_all_pdf_links(self):
        pdf_links = {lang: [] for lang in self.pdf_prefixes.keys()}

        try:
            ftp = FTP(self.ftp_host)
            ftp.login(self.ftp_user, self.ftp_pass)
            ftp.cwd('socnep')

            for lang in pdf_links.keys():
                try:
                    ftp.cwd(lang)
                    files = ftp.nlst()
                    file_dict = {f: True for f in files}

                    for file in files:
                        if file.lower().endswith('.pdf'):
                            encoded_file = urllib.parse.quote(file)
                            url = f"https://socnep.ru/{lang}/{encoded_file}"

                            base_name = file[:-4]
                            txt_name = base_name + '.txt'
                            description = None

                            if txt_name in file_dict:
                                try:
                                    import io
                                    import chardet
                                    txt_data = io.BytesIO()
                                    ftp.retrbinary(f'RETR {txt_name}', txt_data.write)
                                    raw = txt_data.getvalue()
                                    detected = chardet.detect(raw)
                                    encoding = detected.get('encoding', 'utf-8')
                                    description = raw.decode(encoding).strip()
                                    print(f"✅ Описание для {file} загружено (кодировка: {encoding})")
                                except Exception as e:
                                    print(f"⚠️ Ошибка чтения TXT для {file}: {e}")

                            pdf_links[lang].append({
                                'url': url,
                                'description': description,
                                'file': file
                            })
                    ftp.cwd('..')
                except Exception as e:
                    print(f"Ошибка в папке {lang}: {e}")

            ftp.quit()
        except Exception as e:
            print(f"❌ FTP ошибка: {e}")

        return pdf_links

    def get_random_article(self):
        url = "https://api.vk.com/method/wall.get"
        params = {
            "access_token": self.token,
            "owner_id": "-186451829",
            "count": 100,
            "v": "5.199"
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            if "error" in data:
                print(f"Ошибка VK: {data['error']['error_msg']}")
                return None

            items = data["response"]["items"]
            if not items:
                return None

            import random
            random.shuffle(items)

            for post in items:
                if "attachments" in post:
                    for att in post["attachments"]:
                        if att.get("type") == "link":
                            link_url = att["link"]["url"]
                            if "/@-186451829-" in link_url:
                                # Пробуем взять описание из текста поста
                                description = post.get("text", "").strip()

                                # Если текст короткий или начинается со ссылки — парсим страницу
                                if len(description) < 100 or description.startswith('http'):
                                    description = self.get_article_description_from_page(link_url)

                                # Если всё равно пусто — оставляем пустым
                                if not description:
                                    description = ""

                                return {
                                    "url": link_url,
                                    "description": description
                                }

            return None

        except Exception as e:
            print(f"Ошибка получения статьи: {e}")
            return None

    def get_article_description_from_page(self, article_url):
        """Парсит страницу статьи и возвращает первый абзац текста"""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(article_url, headers=headers, timeout=15)

            if response.status_code != 200:
                return ""

            soup = BeautifulSoup(response.text, 'html.parser')

            # Ищем текст в параграфах
            for p in soup.find_all('p'):
                text = p.get_text().strip()
                # Пропускаем короткие и мусорные
                if len(text) > 100 and not text.startswith('http'):
                    # Обрезаем до 500 символов
                    if len(text) > 500:
                        text = text[:497] + "..."
                    return text

            # Если параграфов нет — ищем любой текст в div
            for div in soup.find_all('div', class_='wall_post_text'):
                text = div.get_text().strip()
                if len(text) > 100:
                    if len(text) > 500:
                        text = text[:497] + "..."
                    return text

            return ""
        except Exception as e:
            print(f"Ошибка парсинга страницы: {e}")
            return ""

    def get_random_video_url(self):
        url = "https://api.vk.com/method/video.get"
        params = {
            "access_token": self.token,
            "owner_id": "-186451829",
            "count": 0,
            "v": "5.199"
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            if "error" in data:
                print(f"Ошибка VK API: {data['error']['error_msg']}")
                return None

            items = data.get("response", {}).get("items", [])
            if not items:
                print("Нет видео в группе")
                return None

            video = random.choice(items)
            video_url = f"https://vk.com/video{video['owner_id']}_{video['id']}"
            return video_url

        except Exception as e:
            print(f"Ошибка получения видео: {e}")
            return None

    def get_video_description(self, video_url):
        match = re.search(r'/video-216257056_(\d+)', video_url)
        if not match:
            return ""

        video_id = match.group(1)

        url = "https://api.vk.com/method/video.get"
        params = {
            "access_token": self.token,
            "owner_id": "-186451829",
            "videos": f"-216257056_{video_id}",
            "v": "5.199"
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            if "error" in data:
                return ""

            items = data.get("response", {}).get("items", [])
            if items:
                description = items[0].get("description", "")
                if len(description) > 1000:
                    description = description[:997] + "..."
                return description
        except Exception as e:
            print(f"Ошибка получения описания: {e}")

        return ""

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

    async def publish_next(self):
        index = self.get_current_index()
        item_type, item_name = self.order[index % len(self.order)]

        print(f"\n📢 [{index}] {item_type} - {item_name}")

        if item_type == "playlist":
            video_url = self.get_random_video_url()
            if not video_url:
                print("❌ Не удалось получить видео")
                return

            prefix = self.playlist_prefixes.get(item_name, "")
            description = self.get_video_description(video_url) or ""

            if description:
                message = f"{prefix}\n\n{description}\n\n🎬 Смотреть: {video_url}"
            else:
                message = f"{prefix}\n\n🎬 Смотреть: {video_url}"

        elif item_type == "pdf":
            pdf_links = self.get_all_pdf_links()
            lang = item_name
            if not pdf_links.get(lang):
                print(f"❌ Нет PDF для {lang}")
                return

            item = random.choice(pdf_links[lang])
            pdf_url = item['url']
            description = item.get('description')
            prefix = self.pdf_prefixes.get(lang, "")

            if description:
                message = f"{prefix}\n\n{description}\n\n📄 Читать: {pdf_url}"
            else:
                filename = urllib.parse.unquote(pdf_url.split('/')[-1])
                desc = Path(filename).stem.replace('_', ' ').replace('-', ' ')
                message = f"{prefix}\n\n{desc}\n\n📄 Читать: {pdf_url}"


        elif item_type == "article":
            article = self.get_random_article()
            if not article:
                print("❌ Нет статьи")
                return
            message = f"Книга 📚\n\n{article['description']}\n\n📖 Читать: {article['url']}"

        else:
            return

        if len(message) > 4096:
            message = message[:4093] + "..."

        try:
            self.send_to_channel(message)
            print(f"✅ Опубликовано: {item_type} - {item_name}")
            self.save_current_index((index + 1) % len(self.order))
        except Exception as e:
            print(f"❌ Ошибка публикации: {e}")

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

    def get_video_links_from_playlist(self, playlist_url: str) -> list:
        try:
            # Запускаем yt-dlp, который собирает ссылки на видео
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--flat-playlist",
                    "--print", "webpage_url",  # выводит ссылку на страницу видео
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
        """Отправляет следующее видео по очереди (циклически)"""
        try:
            # Загружаем список, если пустой
            if not self.video_links:
                with open("video_links.txt", "r") as f:
                    self.video_links = f.read().splitlines()

                self.video_links = [link.replace('vk.com', 'vk.ru') for link in self.video_links]

                random.shuffle(self.video_links)

            if not self.video_links:
                return None

            video_url = self.video_links[self.current_video_index]

            # Переходим к следующему
            self.current_video_index = (self.current_video_index + 1) % len(self.video_links)

            # Раз в N видео снова перемешиваем (опционально)
            if self.current_video_index == 0:
                random.shuffle(self.video_links)

            message = f"🎬\n\n{video_url}"
            self.send_to_channel(message)
            return video_url

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None

    async def update_clips(self):
        """Собирает ID клипов и сохраняет чистые ссылки"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.goto("https://vk.ru/clips/plangod", timeout=60000)

            # Скроллим
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(2)

            # Ищем клипы
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

            # Очищаем ссылки: оставляем только clip-owner_id_id
            clean_links = []
            for link in links:
                # Ищем clip-xxx_xxx
                match = re.search(r'(clip-\d+_\d+)', link)
                if match:
                    clean_links.append(f"https://vk.com/{match.group(1)}")

            if clean_links:
                with open(self.clips_file, "w") as f:
                    f.write("\n".join(clean_links))
                print(f"✅ Сохранено {len(clean_links)} клипов")
                for link in clean_links[:5]:
                    print(f"  {link}")
            else:
                print("❌ Клипы не найдены")

    def send_random_clip(self):
        """Отправляет случайный клип в канал MAX"""
        try:
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
            headers = {
                "Authorization": self.bot_token,
                "Content-Type": "application/json"
            }
            payload = {"text": f"🎬\n\n{clip_url}"}

            response = requests.post(url, headers=headers, json=payload, timeout=20)

            if response.status_code == 200:
                print(f"✅ Отправлен клип")
            else:
                print(f"❌ Ошибка отправки: {response.status_code}")

        except Exception as e:
            print(f"❌ Ошибка: {e}")



vk = VkIntegrationNew()
vk.send_random_clip()