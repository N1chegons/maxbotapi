#!/bin/bash
source /home/psylogic/maxapibotnew/venv/bin/activate
cd /home/psylogic/maxapibotnew
python -c "from src.vk.repository import VkIntegrationNew; VkIntegrationNew().post_scheduled_video('$1')"
