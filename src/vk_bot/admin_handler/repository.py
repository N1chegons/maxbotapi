from src.logger_config import setup_logger

VK_ADMIN_IDS = [552367635, 420142]
logger = setup_logger('admin_repository_vk', 'vk', 'admin_repository_vk.log')

class VkAdminRepository:
    @classmethod
    def is_admin(cls, user_id: int):
        return user_id in VK_ADMIN_IDS