import asyncio
import sys
import logging

project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.tochka_api.auto_payment import auto_charge_active_subscriptions, auto_charge_after_trial

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/psylogic/maxapibotnew/logs/auto_charge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    await auto_charge_active_subscriptions()
    await auto_charge_after_trial()

if __name__ == "__main__":
    asyncio.run(main())