#!/home/psylogic/maxapibotnew/venv/bin/python
import sys
import os

# Добавляем путь к корню проекта
project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

# Теперь импорты будут работать
from src.vk.repository import VkIntegrationNew

if __name__ == "__main__":
    vk = VkIntegrationNew()
    vk.send_random_video()