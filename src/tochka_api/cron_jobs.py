import asyncio
import sys
from datetime import datetime

project_root = '/home/psylogic/maxapibotnew'
sys.path.insert(0, project_root)

from src.logger_config import setup_logger
from src.tochka_api.auto_payment import (
    auto_charge_active_subscriptions,
    auto_charge_active_subscriptions_dominator
)

logger = setup_logger('cron_jobs', 'cron', 'cron_jobs.log')


async def main():
    start_time = datetime.utcnow()
    logger.info("=" * 50)
    logger.info(f"🔄 ЗАПУСК CRON-ЗАДАЧ В {start_time}")
    logger.info("=" * 50)

    try:
        # ✅ Автосписание для обычного бота
        logger.info("📌 Запуск автосписания для обычного бота...")
        await auto_charge_active_subscriptions()
        logger.info("✅ Автосписание для обычного бота завершено")

        # ✅ Автосписание для доминант-бота
        logger.info("📌 Запуск автосписания для доминант-бота...")
        await auto_charge_active_subscriptions_dominator()
        logger.info("✅ Автосписание для доминант-бота завершено")

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"✅ ВСЕ ЗАДАЧИ ВЫПОЛНЕНЫ ЗА {duration:.2f} СЕКУНД")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В CRON: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())