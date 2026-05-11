#!/home/psylogic/maxapibotnew/venv/bin/python
import subprocess
import json
import re
import os

PLAYLISTS = [
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


def get_video_links():
    all_links = []
    for playlist in PLAYLISTS:
        print(f"Обработка {playlist}...")
        try:
            # Пробуем через yt-dlp
            result = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--print", "webpage_url", playlist],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                links = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                # Убираем дубликаты внутри плейлиста
                links = list(dict.fromkeys(links))
                all_links.extend(links)
                print(f"  Найдено: {len(links)} видео")
            else:
                print(f"  Ошибка: {result.stderr[:200]}")
        except Exception as e:
            print(f"  Ошибка: {e}")

    # Убираем дубликаты общие
    all_links = list(dict.fromkeys(all_links))
    return all_links


def save_links(links):
    with open("video_links.txt", "w") as f:
        f.write("\n".join(links))
    print(f"\n✅ Сохранено {len(links)} уникальных видео")


if __name__ == "__main__":
    links = get_video_links()
    if links:
        save_links(links)
    else:
        print("❌ Не удалось получить ссылки")