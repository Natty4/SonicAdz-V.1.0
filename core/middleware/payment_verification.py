from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.utils.timezone import now

from payments.models import UserPaymentMethod
from core.models import CreatorChannel, Notification
from users.models import UserType
from core.utils.notification import send_telegram_notification


class CreatorPaymentVerificationMiddleware(MiddlewareMixin):
    """
    Ensures that 'creator' users have at least one verified payment method (wallet or bank).
    If not, a notification and a Telegram alert are sent.
    """

    def process_request(self, request):
        user = request.user

        if not user.is_authenticated or user.user_type != UserType.CREATOR:
            return

        has_any_payment_method = UserPaymentMethod.objects.filter(user=user).exists()

      
        if has_any_payment_method:
            has_verified_method = UserPaymentMethod.objects.filter(
                user=user,
                status=UserPaymentMethod.Status.VERIFIED
            ).exists()

            if has_verified_method:
                return

        # Proceed only if the creator channel is verified
        has_verified_channel = CreatorChannel.objects.filter(
            owner=user,
            status=CreatorChannel.ChannelStatus.VERIFIED
        ).exists()

        if not has_verified_channel:
            return

        session_flag = '_payment_method_warning_sent'
        if request.session.get(session_flag):
            return

        Notification.objects.create(
            user=user,
            title="Action Required: Verify Your Payment Method",
            message="⚠️ You must have at least one verified payment method (wallet or bank account) to be eligible for payouts.",
            type="payment"
        )

        try:
            if hasattr(user, 'telegram_profile') and user.telegram_profile.tg_id:
                send_telegram_notification(
                    chat_id=user.telegram_profile.tg_id,
                    text=(
                        "🔔 *Action Required!*\n\n"
                        "You must have at least one verified payment method "
                        "(wallet or bank account) to receive payouts."
                    )
                )
        except Exception as e:
            if settings.DEBUG:
                print(f"[PaymentVerificationMiddleware] Telegram error: {e}")

        request.session[session_flag] = True