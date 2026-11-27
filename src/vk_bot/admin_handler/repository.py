import re

from src.logger_config import setup_logger

VK_ADMIN_IDS = [552367635, 420142]
logger = setup_logger('admin_repository_vk', 'vk', 'admin_repository_vk.log')

class VkAdminRepository:
    @classmethod
    def is_admin(cls, user_id: int):
        return user_id in VK_ADMIN_IDS

    @classmethod
    def get_display_id(cls, url: str, fallback_id: int) -> str:
        if not url:
            return str(fallback_id)

        match = re.search(r'(\d+)(?!.*\d)', url)
        if match:
            return match.group(1)[-3:]
        return str(fallback_id)