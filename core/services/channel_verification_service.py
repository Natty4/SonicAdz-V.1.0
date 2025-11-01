import logging
import requests
from django.conf import settings
from core.utils.notification import send_telegram_notification
from core.models import Notification
from creators.models import CreatorChannel
from users.models import User

logger = logging.getLogger(__name__)


def verify_creator_channel(channel: CreatorChannel) -> bool:
    """
    Verifies a single CreatorChannel's bot admin status.
    If the bot is no longer admin with post permission, update channel and notify.
    
    Returns True if still valid, False otherwise.
    """
    try:
        if not channel.channel_id:
            logger.warning(f"Channel {channel.id} missing channel_id. Skipping.")
            return False

        is_admin, can_post = check_bot_admin_status(channel.channel_id)

        if is_admin and can_post:
            if channel.is_active:
                channel.status = CreatorChannel.ChannelStatus.VERIFIED
                channel.save(update_fields=["status", "updated_at"])
            return True

        user = channel.owner

        # Determine the specific reason for failure
        if not is_admin:
            text = (
                f"🚨 *Verification Issue with {channel.title}*\n\n"
                f"Our bot is no longer an admin in your channel.\n"
                f"Please add the bot back as admin with *post permission* "
                f"to keep your channel verified."
            )
        elif not can_post:
            text = (
                f"🚨 *Verification Issue with {channel.title}*\n\n" 
                f"Our bot does *not* have *post permission*. Please enable *Post Permission* " 
                f"to keep your channel verified and eligiable to receive ads."
            )
        else:
            text = (
                f"⚠️ Unknown issue verifying your channel *{channel.title}*. Please check bot permissions."
            )

        # Downgrade channel
        channel.status = CreatorChannel.ChannelStatus.PENDING
        channel.save(update_fields=["status", "updated_at"])

        # Internal notification
        Notification.objects.create(
            user=user,
            title="Channel Verification Failed",
            message=(
                f"⚠️ Your channel *{channel.title}* is no longer verified.\n\n"
                f"Please make sure our Telegram bot is added as an admin atleast with post permission "
                f"to continue receiving ads and earnings."
            ),
            type="Verify",
        )

        # Telegram message
        if hasattr(user, 'telegram_profile') and user.telegram_profile.tg_id:
            send_telegram_notification(
                chat_id=user.telegram_profile.tg_id,
                text=text
            )

        return False

    except Exception as e:
        logger.error(f"Error verifying channel {channel.id}: {e}", exc_info=True)
        return False


def check_bot_admin_status(channel_id: str) -> tuple[bool, bool]:
    """
    Calls Telegram Bot API to get bot's status in the given channel.
    Returns a tuple (is_admin, can_post).
    """
    url = f"https://api.telegram.org/bot{settings.BOT_SECRET_TOKEN}/getChatMember"
    params = {
        "chat_id": channel_id,
        "user_id": settings.BOT_ID
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code != 200:
            logger.warning(f"Failed to get bot status for {channel_id}: {response.text}")
            return False, False

        data = response.json()
        result = data.get("result", {})
        is_admin = result.get("status") == "administrator"
        can_post = result.get("can_post_messages", False)

        return is_admin, can_post

    except requests.RequestException as e:
        logger.error(f"Telegram API error while checking bot admin status: {e}")
        return False, False