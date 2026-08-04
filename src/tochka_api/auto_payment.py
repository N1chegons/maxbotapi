from sqlalchemy import update

from src.db import async_session
from src.logger_config import setup_logger
from src.max.manager_sending import send_notification_max, send_notification_max_2
from src.max.models import SubsStatus, User
from src.max.repository import MaxService
from src.telegram.manager_sending import send_notification_telegram
from src.tochka_api.service import TochkaApiService


logger = setup_logger('auto_payment', 'tochka_api', 'auto_payment.log')


async def auto_charge_active_subscriptions():
    """Автосписание для обычного бота (MAX_Empathetic)"""
    logger.info("🔄 Запуск auto_charge_active_subscriptions")
    users = await MaxService.get_users_for_auto_charge()
    logger.info(f"📋 Найдено пользователей для списания: {len(users)}")

    for user in users:
        logger.info(f"👤 Обработка пользователя {user.user_id}, payment_method_id: {user.payment_method_id}")

        if not user.payment_method_id:
            logger.warning(f"❌ У пользователя {user.user_id} нет payment_method_id, пропускаем")
            continue

        logger.info(f"💰 Попытка списания 1111 ₽ для пользователя {user.user_id}")
        success = TochkaApiService().charge_payments(1111.00, user.payment_method_id)

        if success:
            logger.info(f"✅ Списание инициировано для {user.user_id}")
            if user.platform == "MAX":
                await send_notification_max(user.user_id, "💰 Производится списание 1111 ₽")
            else:
                await send_notification_telegram(user.user_id, "💰 Производится списание 1111 ₽")
        else:
            logger.error(f"❌ Ошибка списания для {user.user_id}")
            await handle_failed_charge(user)


async def handle_failed_charge(user):
    """Обработка неудачного списания для обычного бота"""
    new_attempts = (user.grace_period_attempts or 0) + 1
    logger.warning(f"⚠️ Неудачное списание для {user.user_id}, попытка {new_attempts}/3")

    await MaxService.update_grace_period_attempts(user.user_id, new_attempts)
    await MaxService.change_subscription_status(user.user_id, SubsStatus.grace_period)

    if new_attempts >= 3:
        logger.error(f"❌ 3 неудачных попытки для {user.user_id}, подписка отключена")
        await MaxService.change_subscription_status(user.user_id, SubsStatus.expired)
        if user.platform == "MAX":
            await send_notification_max(user.user_id, "❌ Подписка отключена. Оплатите в /sub")
        else:
            await send_notification_telegram(user.user_id, "❌ Подписка отключена. Оплатите в /sub")
        return
    else:
        logger.info(f"🔄 Повторная попытка запланирована для {user.user_id}, попытка {new_attempts}/3")
        if user.platform == "MAX":
            await send_notification_max(
                user.user_id,
                f"⚠️ Не удалось списать {new_attempts}/3. Повторная попытка завтра."
            )
        else:
            await send_notification_telegram(
                user.user_id,
                f"⚠️ Не удалось списать {new_attempts}/3. Повторная попытка завтра."
            )


async def auto_charge_active_subscriptions_dominator():
    """Автосписание для доминант-бота (MAX_Dominator)"""
    logger.info("🔄 Запуск auto_charge_active_subscriptions_dominator")
    users = await MaxService.get_users_for_auto_charge_dominator()
    logger.info(f"📋 Найдено пользователей для списания (доминант): {len(users)}")

    for user in users:
        logger.info(f"👤 Обработка пользователя {user.user_id} (доминант)")

        if not user.payment_method_id:
            logger.warning(f"❌ У пользователя {user.user_id} нет payment_method_id, пропускаем")
            continue

        logger.info(f"💰 Попытка списания 333 ₽ для пользователя {user.user_id} (доминант)")
        success = TochkaApiService().charge_payments(333.00, user.payment_method_id)

        if success:
            logger.info(f"✅ Списание инициировано для {user.user_id} (доминант)")
            await send_notification_max_2(user.user_id, "💰 Производится списание 333 ₽")
        else:
            logger.error(f"❌ Ошибка списания для {user.user_id} (доминант)")
            await handle_failed_charge_dominator(user)


async def handle_failed_charge_dominator(user):
    """Обработка неудачного списания для доминант-бота"""
    new_attempts = (user.grace_period_attempts_dominator or 0) + 1
    logger.warning(f"⚠️ Неудачное списание для {user.user_id} (доминант), попытка {new_attempts}/3")

    # Обновляем попытки для доминант-бота
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.user_id == user.user_id)
            .values(grace_period_attempts_dominator=new_attempts)
        )
        await session.commit()

    # Меняем статус подписки доминант-бота
    await MaxService.change_subscription_status_dominator(user.user_id, SubsStatus.grace_period)

    if new_attempts >= 3:
        logger.error(f"❌ 3 неудачных попытки для {user.user_id} (доминант), подписка отключена")
        await MaxService.change_subscription_status_dominator(user.user_id, SubsStatus.expired)
        await send_notification_max_2(
            user.user_id,
            "❌ Подписка на доминант-бота отключена. Оплатите в /sub_dominator"
        )
        return
    else:
        logger.info(f"🔄 Повторная попытка запланирована для {user.user_id} (доминант), попытка {new_attempts}/3")
        await send_notification_max_2(
            user.user_id,
            f"⚠️ Не удалось списать {new_attempts}/3. Повторная попытка завтра."
        )