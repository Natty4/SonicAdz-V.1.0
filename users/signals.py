from allauth.account.signals import email_confirmed
from django.dispatch import receiver

@receiver(email_confirmed)
def update_email_verified(sender, request, email_address, **kwargs):
    try:
        user = email_address.user
        if user and not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating email_verified for user {email_address.user.id}: {e}")