import asyncio
import sys

project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.tochka_api.auto_payment import auto_charge_active_subscriptions

async def main():
    await auto_charge_active_subscriptions()

if __name__ == "__main__":
    asyncio.run(main())