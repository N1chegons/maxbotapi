import re
import asyncio
from vkbottle import API
from src.config import settings
from src.vk_bot.repository import VkFactRepository


class FactSenderService:
    VK_TOKEN = settings.VK_TOKEN_COMMUNITY
    # Внимание: ID сообщества с минусом
    GROUP_ID = -216257056
    api = API(VK_TOKEN)

    @classmethod
    async def send_fact(cls):
        # 1. Получаем факт
        fact = await VkFactRepository.get_random_fact()

        if not fact:
            print("❌ Фактов в базе нет.")
            return

        # 2. Формируем текст (исправлена опечатка tiitle -> title)
        post_text = fact.title

        # 3. Парсим ссылку (исправлено url -> video_url, если в модели так)
        # Если в модели поле называется url, то оставь fact.url
        full_url = fact.video_url if hasattr(fact, 'video_url') else fact.url

        attachment = None
        if full_url:
            match = re.search(r'(video-?\d+_\d+)', full_url)
            if match:
                attachment = match.group(1)
            else:
                attachment = full_url

        try:
            response = await cls.api.wall.post(
                owner_id=cls.GROUP_ID,  # Тут минус уже есть
                from_group=1,
                message=post_text,
                attachments=attachment
            )

            # Достаем ID поста из ответа
            post_id = response.post_id

            print(f"✅ ПОБЕДА! Пост успешно опубликован.")
            # Добавил нижнее подчеркивание _ перед ID
            print(f"Ссылка на пост: https://vk.com/wall{cls.GROUP_ID}_{post_id}")

        except Exception as e:
            print(f"❌ Ошибка публикации: {e}")


async def main():
    await FactSenderService.send_fact()


if __name__ == '__main__':
    asyncio.run(main())