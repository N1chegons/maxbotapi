import asyncio
from vkbottle import API
from src.config import settings

VK_TOKEN = settings.VK_TOKEN_COMMUNITY
GROUP_ID = 216257056

TEST_FACT_TEXT = "В 1915 году химик Зелинский создал противогаз, в основе которого был активированный уголь."
# Правильный формат вложения для ВК (без URL)
TEST_VIDEO_ATTACHMENT = "video-216257056_456240746"

async def main():
    print("1. Инициализация API...")
    api = API(VK_TOKEN)

    try:
        print("2. Проверка токена...")
        # В vkbottle 4.x groups.get_by_id возвращает объект, а не список.
        # Название группы лежит в поле 'title', а не 'name'.
        group_info = await api.groups.get_by_id(group_id=GROUP_ID)
        print(f"✅ Токен валиден. Сообщество: {group_info.title}")
    except Exception as e:
        print(f"❌ Ошибка токена: {e}")
        return

    print("3. Формирование поста...")
    post_text = f"💡 Факт дня\n\n{TEST_FACT_TEXT}\n\nПодробнее смотри в видео 👇"

    print("4. Публикация на стену (wall.post)...")
    try:
        response = await api.wall.post(
            owner_id=-GROUP_ID,
            from_group=1,
            message=post_text,
            attachments=TEST_VIDEO_ATTACHMENT # Передаем правильный ID видео
        )
        print(f"✅ ПОБЕДА! Пост успешно опубликован.")
        print(f"ID записи: {response}")
        print(f"Ссылка на пост: https://vk.com/wall-{GROUP_ID}_{response}")
    except Exception as e:
        print(f"❌ Ошибка публикации: {e}")

if __name__ == "__main__":
    asyncio.run(main())