import random
import requests
import re
from ftplib import FTP
from bs4 import BeautifulSoup
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
            "Здоровье": "https://vkvideo.ru/video-216257056_456240516?pl=-216257056_8",
            "Сила": "https://vkvideo.ru/video-216257056_456240512?pl=-216257056_7",
            "Специалисты": "https://vkvideo.ru/video-216257056_456240512?pl=-216257056_6",
            "Логистика": "https://vkvideo.ru/video-216257056_456240485?pl=-216257056_5",
            "Строительство": "https://vkvideo.ru/video-216257056_456240485?pl=-216257056_4",
            "Питание": "https://vkvideo.ru/video-216257056_456240485?pl=-216257056_3",
            "Педагогика": "https://vkvideo.ru/video-216257056_456240485?pl=-216257056_2",
            "Машиностроение": "https://vkvideo.ru/video-216257056_456240485?pl=-216257056_1",
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
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            import urllib.parse
                            encoded_file = urllib.parse.quote(file)
                            url = f"https://socnep.ru/socnep/{lang}/{encoded_file}"
                            pdf_links[lang].append(url)
                    ftp.cwd('..')
                except Exception as e:
                    print(f"Ошибка в папке {lang}: {e}")

            ftp.quit()
        except Exception as e:
            print(f"❌ FTP ошибка: {e}")

        return pdf_links

    def get_article_links(self):
        article_links = []
        try:
            # Парсим страницу библиотеки
            url = "https://vk.ru/socnep.biblio"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            for link in soup.find_all('a', href=True):
                if '/doc' in link['href']:
                    full_url = "https://vk.ru" + link['href']
                    article_links.append(full_url)
        except Exception as e:
            print(f"Ошибка получения статей: {e}")

        return article_links

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
                print(f"API ошибка: {data['error']['error_msg']}")
                return ""

            items = data.get("response", {}).get("items", [])
            if items:
                description = items[0].get("description", "")
                if len(description) > 500:
                    description = description[:497] + "..."
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
            description = self.get_video_description(video_url)
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
            pdf_url = random.choice(pdf_links[lang])
            prefix = self.pdf_prefixes.get(lang, "")
            message = f"{prefix}\n\n📄 Читать: {pdf_url}"

        elif item_type == "article":
            articles = self.get_article_links()
            if not articles:
                print("❌ Нет статей")
                return
            article_url = random.choice(articles)
            message = f"Книга 📚\n\n📖 Читать: {article_url}"

        else:
            return

        if len(message) > 4096:
            message = message[:4093] + "..."

        try:
            self.send_to_channel(message)
            print(f"✅ Опубликовано: {item_type} - {item_name}")
            self.save_current_index((index + 1) % len(self.order))
        except Exception as e:
            print(f"❌ Ошибка: {e}")

