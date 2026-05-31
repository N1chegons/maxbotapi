import asyncio
import sys

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.tochka_api.auto_payment import auto_charge_active_subscriptions, auto_charge_after_trial

async def main():
    await auto_charge_active_subscriptions()
    await auto_charge_after_trial()

if __name__ == "__main__":
    asyncio.run(main())