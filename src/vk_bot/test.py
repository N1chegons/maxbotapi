import asyncio
import random
from vkbottle import API

from src.config import settings

# --- НАСТРОЙКИ ---
# Вставь сюда свой токен (который с правами управления)
VK_TOKEN = settings.VK_TOKEN_COMMUNITY
# ID твоего сообщества (без минуса, просто цифры из ссылки club216257056)
GROUP_ID = 216257056

# Тестовые данные (потом они будут браться из БД)
TEST_FACT_TEXT = "В 1915 году химик Зелинский создал противогаз, в основе которого был активированный уголь."
TEST_VIDEO_URL = "https://vkvideo.ru/video-216257056_456240746?pl=-216257056_2"

async def main():
    print("1. Инициализация API...")
    api = API(VK_TOKEN)

    # Сначала проверим, чей это токен и есть ли права
    try:
        print("2. Проверка токена...")
        me = await api.users.get()
        print(f"✅ Токен валиден. Владелец токена: {me[0].first_name} {me[0].last_name}")
    except Exception as e:
        print(f"❌ Ошибка токена: {e}")
        return

    print("3. Формирование поста...")
    # Формируем текст. В ВК нет Markdown, поэтому используем просто текст
    post_text = f"💡 Факт дня\n\n{TEST_FACT_TEXT}\n\nПодробнее смотри в видео 👇"

    print("4. Публикация на стену (wall.post)...")
    try:
        response = await api.wall.post(
            owner_id=-GROUP_ID, # Внимание: для сообществ ID пишется с минусом
            from_group=1,       # Публикуем от имени сообщества
            message=post_text,
            attachments=TEST_VIDEO_URL
        )
        print(f"✅ ПОБЕДА! Пост успешно опубликован.")
        print(f"ID записи: {response}")
        print(f"Ссылка на пост: https://vk.com/wall-{GROUP_ID}_{response}")
    except Exception as e:
        print(f"❌ Ошибка публикации: {e}")

if __name__ == "__main__":
    asyncio.run(main())