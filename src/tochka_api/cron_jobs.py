import asyncio
import sys

project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.tochka_api.auto_payment import (
    auto_charge_active_subscriptions,
    auto_charge_active_subscriptions_dominator
)


async def main():
    await auto_charge_active_subscriptions()

    await auto_charge_active_subscriptions_dominator()


if __name__ == "__main__":
    asyncio.run(main())