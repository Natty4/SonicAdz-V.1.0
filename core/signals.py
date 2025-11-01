from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from core.models import Campaign, AdPlacement, Notification
from payments.models import Transaction, WithdrawalRequest
from core.utils.signals_utils import process_campaign_activation, process_placement_approval
from core.utils.notification import send_telegram_notification

import logging

logger = logging.getLogger(__name__)







@receiver(post_save, sender=Campaign)
def handle_campaign_status_change(sender, instance, created, **kwargs):
    if not created and instance.status == 'active':
        process_campaign_activation(instance)

@receiver(post_save, sender=AdPlacement)
def handle_placement_status_change(sender, instance, created, **kwargs):
    if not created and instance.status == 'approved':
        process_placement_approval(instance)



TRACKED_FIELDS = [
    "initial_budget",
    "cpm",
    "objective",
]
   
@receiver(pre_save, sender=Campaign)
def cache_previous_campaign_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_state = None
        return
    try:
        instance._previous_state = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._previous_state = None
        
@receiver(post_save, sender=Campaign)
def handle_campaign_tracked_field_changes(sender, instance, created, **kwargs):
    if created or instance.status not in ['active', 'completed']:
        return

    previous = getattr(instance, '_previous_state', None)
    if not previous:
        return

    changed_fields = []

    # Basic fields
    for field in TRACKED_FIELDS:
        if getattr(previous, field) != getattr(instance, field):
            changed_fields.append(field)

    # M2M fields
    previous_languages = set(previous.targeting_languages.values_list('pk', flat=True))
    current_languages = set(instance.targeting_languages.values_list('pk', flat=True))

    if previous_languages != current_languages:
        changed_fields.append("targeting_languages")

    previous_categories = set(previous.targeting_categories.values_list('pk', flat=True))
    current_categories = set(instance.targeting_categories.values_list('pk', flat=True))

    if previous_categories != current_categories:
        changed_fields.append("targeting_categories")

    if changed_fields:

        # Temporarily disable signal triggering inside this save
        from django.db.models.signals import post_save
        post_save.disconnect(handle_campaign_tracked_field_changes, sender=Campaign)

        instance.status = 'active'
        instance.save(update_fields=['status'])

        post_save.connect(handle_campaign_tracked_field_changes, sender=Campaign)

        process_campaign_activation(instance)
        
        
@receiver(post_save, sender=AdPlacement)
def notify_ad_action(sender, instance, created, **kwargs):
    if not created and instance.status in ['approved', 'running', 'rejected', 'paused', 'completed']:
        title = f"Ad Placement {instance.status.title()}"
        message = f"The ad '{instance.ad.headline}' on your channel '{instance.channel.title}' has been {instance.status}."

        # Create in-app notification
        Notification.objects.create(
            user=instance.channel.owner,
            title=title,
            message=message,
            type='Adz'
        )

        # Send Telegram notification ONLY if status is 'running'
        if instance.status == 'running':
            try:
                tg_id = instance.channel.owner.telegram_profile.tg_id
                if tg_id:
                    tg_message = (
                        f"🎉 Congrats new ad match!\n"
                        f"The ad \"{instance.ad.headline}\" has been matched and approved "
                        f"for your channel \"{instance.channel.title}\" and is now **Live**!"
                    )
                    send_telegram_notification(tg_id, tg_message)
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")
                

@receiver(post_save, sender=Transaction)
def notify_earning(sender, instance, created, **kwargs):
    if created and instance.transaction_type == 'credit':
        title = "New Earning Recorded"
        message = f"You have received a new earning of {instance.amount:.2f} for ad performance."
        try:
            Notification.objects.create(
                user=instance.user,
                title=title,
                message=message,
                type='Earning',
                is_active=False
            )
            # Telegram notification
            tg_id = instance.user.telegram_profile.tg_id
            if tg_id:
                tg_message = (
                        f"💰 *New Weekly Earning!*\n"
                        f"You just earned *{instance.amount:.2f} ETB* from last week's ad performance.\n"
                        f"Keep growing your channel!"
                    )
                send_telegram_notification(tg_id, tg_message)

            logger.info(f"Earning notification created for user {instance.user.username}, amount {instance.amount}")

        except Exception as e:
            logger.error(f"Failed to create earning notification: {e}")


@receiver(post_save, sender=WithdrawalRequest)
def notify_withdrawal(sender, instance, created, **kwargs):
    if not created and instance.status in ['approved', 'rejected', 'completed']:
        user = instance.user_payment_method.user
        amount = f"{instance.amount:.2f} ETB"
        reference = instance.reference

        status_messages = {
            'approved': {
                'title': "Withdrawal Request Approved",
                'message': (
                    f"Great news, {user}! Your withdrawal request for {amount} (Ref: {reference}) "
                    f"has been approved. The funds will be processed to your payment method "
                    f"({instance.user_payment_method}) soon. Expect the transfer within 1–3 business days."
                ),
                'tg_message': (
                    f"✅ *Withdrawal Approved*\n"
                    f"You requested *{amount}* (Ref: `{reference}`)\n"
                    f"Your payment is being processed. Expect it within 1–3 business days."
                )
            },
            'rejected': {
                'title': "Withdrawal Request Rejected",
                'message': (
                    f"Hi {user}, your withdrawal request for {amount} (Ref: {reference}) "
                    f"was rejected. Please check your payment method details or contact support for assistance."
                ),
                'tg_message': (
                    f"❌ *Withdrawal Rejected*\n"
                    f"*{amount}* (Ref: `{reference}`) could not be processed.\n"
                    f"Please review your payment method or contact support."
                )
            },
            'completed': {
                'title': "Withdrawal Request Completed",
                'message': (
                    f"Success, {user}! Your withdrawal of {amount} (Ref: {reference}) "
                    f"has been completed and transferred to your payment method "
                    f"({instance.user_payment_method}). Check your account!"
                ),
                'tg_message': (
                    f"🎉 *Withdrawal Completed*\n"
                    f"*{amount}* (Ref: `{reference}`) has been sent to your account.\n"
                    f"Please check your payment method."
                )
            },
        }

        notification = status_messages.get(instance.status.lower(), {})
        title = notification.get('title', f"Withdrawal Request {instance.status.title()}")
        message = notification.get('message', f"Your withdrawal request for {amount} (Ref: {reference}) has been {instance.status}.")
        tg_message = notification.get('tg_message')

        # Create in-app notification
        try:
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                type='Withdrawal',
                is_active=True
            )
            logger.info(f"Withdrawal notification created for user {user.username}, status {instance.status}, ref {reference}")
        except Exception as e:
            logger.error(f"Failed to create withdrawal notification for ref {reference}: {e}")

        # Send Telegram notification
        try:
            tg_id = user.telegram_profile.tg_id
            if tg_id and tg_message:
                send_telegram_notification(tg_id, tg_message)
        except Exception as e:
            logger.error(f"Failed to send Telegram withdrawal message for ref {reference}: {e}")
            
    