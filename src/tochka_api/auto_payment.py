from src.logger_config import setup_logger
from src.max.manager_sending import send_notification_max
from src.max.models import SubsStatus
from src.max.repository import MaxService
from src.telegram.manager_sending import send_notification_telegram
from src.tochka_api.service import TochkaApiService


logger = setup_logger('auto_payment', 'tochka_api', 'auto_payment.log')


async def auto_charge_active_subscriptions():
    logger.info("🔄 Запуск auto_charge_active_subscriptions")
    users = await MaxService.get_users_for_auto_charge()
    logger.info(f"📋 Найдено пользователей для списания: {len(users)}")

    for user in users:
        logger.info(f"👤 Обработка пользователя {user.user_id}, payment_method_id: {user.payment_method_id}")

        if not user.payment_method_id:
            logger.warning(f"❌ У пользователя {user.user_id} нет payment_method_id, пропускаем")
            continue

        logger.info(f"💰 Попытка списания 650 ₽ для пользователя {user.user_id}")
        success = TochkaApiService().charge_payments(650.00, user.payment_method_id)

        if success:
            logger.info(f"✅ Списание инициировано для {user.user_id}")
            if user.platform == "MAX":
                await send_notification_max(user.user_id, "💰 Производится списание 650 ₽")
            else:
                await send_notification_telegram(user.user_id, "💰 Производится списание 650 ₽")
        else:
            logger.error(f"❌ Ошибка списания для {user.user_id}")
            await handle_failed_charge(user)


async def auto_charge_after_trial():
    logger.info("🔄 Запуск auto_charge_after_trial")
    users = await MaxService.get_users_with_expired_trial()
    logger.info(f"📋 Найдено пользователей с истекшим триалом: {len(users)}")

    for user in users:
        logger.info(f"👤 Обработка пользователя {user.user_id}, payment_method_id: {user.payment_method_id}")

        if not user.payment_method_id:
            logger.warning(f"❌ У пользователя {user.user_id} нет payment_method_id, переводим в expired")
            await MaxService.change_subscription_status(user.user_id, SubsStatus.expired)
            if user.platform == "MAX":
                await send_notification_max(
                    user.user_id,
                    "⚠️ Ваш пробный период закончился. Оплатите подписку в /sub"
                )
            else:
                await send_notification_telegram(
                    user.user_id,
                    "⚠️ Ваш пробный период закончился. Оплатите подписку в /sub"
                )
            continue

        logger.info(f"💰 Попытка списания 650 ₽ для пользователя {user.user_id} (после триала)")
        success = TochkaApiService().charge_payments(650.00, user.payment_method_id)

        if success:
            logger.info(f"✅ Списание инициировано для {user.user_id}, активируем подписку")
            await MaxService.activate_subscription_after_trial(user.user_id)
            if user.platform == "MAX":
                await send_notification_max(user.user_id, "💰 Триал закончился, списано 650 ₽")
            else:
                await send_notification_telegram(user.user_id, "💰 Триал закончился, списано 650 ₽")
        else:
            logger.error(f"❌ Ошибка списания для {user.user_id} (после триала)")
            await handle_failed_charge(user)


async def handle_failed_charge(user):
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