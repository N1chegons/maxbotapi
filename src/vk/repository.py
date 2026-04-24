import asyncio
import random
import requests
import re
import urllib.parse
from pathlib import Path
from ftplib import FTP
from src.config import settings


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

            # Фильтруем посты с текстом
            valid_posts = [p for p in items if p.get("text") and len(p["text"]) > 50]
            if not valid_posts:
                valid_posts = items

            post = random.choice(valid_posts)
            post_id = post["id"]
            text = post["text"]

            # Берём первый абзац (до первой пустой строки или перевода строки)
            first_paragraph = text.split('\n\n')[0].strip().split('\n')[0].strip()

            # Если первый абзац — это ссылка, берём следующий
            if first_paragraph.startswith('http') or first_paragraph.startswith('https://vk.ru'):
                parts = text.split('\n\n')
                for part in parts:
                    if part.strip() and not part.startswith('http'):
                        first_paragraph = part.strip()
                        break

            # Ограничиваем длину
            if len(first_paragraph) > 500:
                first_paragraph = first_paragraph[:497] + "..."

            article_url = f"https://vk.ru/@socnep.biblio-{post_id}"

            return {
                "url": article_url,
                "description": first_paragraph
            }
        except Exception as e:
            print(f"Ошибка получения статьи: {e}")
            return None

    def get_video_description(self, video_url):
        match = re.search(r'/video-216257056_(\d+)', video_url)
        if not match:
            return ""

        video_id = match.group(1)

        url = "https://api.vk.com/method/video.get"
        params = {
            "access_token": self.token,
            "owner_id": self.group_id,
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
            video_url = self.video_urls.get(item_name)
            if not video_url:
                print(f"❌ Нет видео для {item_name}")
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
            article = self.get_random_article()  # ← новый метод
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