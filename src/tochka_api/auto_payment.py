from src.max.manager_sending import send_notification_max
from src.max.models import SubsStatus
from src.max.repository import MaxService
from src.telegram.manager_sending import send_notification_telegram
from src.tochka_api.service import TochkaApiService


async def auto_charge_active_subscriptions():
    users = await MaxService.get_users_for_auto_charge()

    for user in users:
        if not user.payment_method_id:
            continue

        success = TochkaApiService().charge_payments(650.00, user.payment_method_id)

        if success:
            if user.platform == "MAX":
                await send_notification_max(user.user_id, "💰 Производится списание 650 ₽")
            else:
                await send_notification_telegram(user.user_id, "💰 Производится списание 650 ₽")
        else:
            await handle_failed_charge(user)


async def auto_charge_after_trial():
    users = await MaxService.get_users_with_expired_trial()

    for user in users:
        if not user.payment_method_id:
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

        success = TochkaApiService().charge_payments(650.00, user.payment_method_id)

        if success:
            await MaxService.activate_subscription_after_trial(user.user_id)
            if user.platform == "MAX":
                await send_notification_max(user.user_id, "💰 Триал закончился, списано 650 ₽")
            else:
                await send_notification_telegram(user.user_id, "💰 Триал закончился, списано 650 ₽")
        else:
            await handle_failed_charge(user)


async def handle_failed_charge(user):
    new_attempts = (user.grace_period_attempts or 0) + 1
    await MaxService.update_grace_period_attempts(user.user_id, new_attempts)
    await MaxService.change_subscription_status(user.user_id, SubsStatus.grace_period)

    if new_attempts >= 3:
        await MaxService.change_subscription_status(user.user_id, SubsStatus.expired)
        if user.platform == "MAX":
            await send_notification_max(user.user_id, "❌ Подписка отключена. Оплатите в /sub")

        else:
            await send_notification_telegram(user.user_id, "❌ Подписка отключена. Оплатите в /sub")

        return
    else:
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