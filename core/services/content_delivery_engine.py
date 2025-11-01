import logging
from django.utils import timezone
from core.models import AdPlacement, AdPlacementStatus
from core.utils.bot_utils import TelegramBotUtil

logger = logging.getLogger(__name__)

class ContentDeliveryService:
    def __init__(self, bot_token):
        self.bot_util = TelegramBotUtil(bot_token)

    def post_to_channel(self, placement):
        """Post an ad to a Telegram channel and update the AdPlacement model."""
        try:
            ad = placement.ad
            result = self.bot_util.send_message_to_channel(
                channel_id=placement.channel.channel_id,
                text_content=ad.text_content,
                headline=ad.headline,
                image_url=ad.img_url,
                social_links=ad.social_links,
                brand_name=ad.brand_name,
                hashtags=ad.hashtags if hasattr(ad, 'hashtags') else None
            )
            if result["success"]:
                placement.content_platform_id = result["link"]
                placement.status = AdPlacementStatus.RUNNING
                placement.save(update_fields=["content_platform_id", "status"])
                logger.info(f"Posted to Telegram for placement {placement.id}, channel {placement.channel.title}")
                return result
            else:
                logger.error(f"Failed to post to Telegram for placement {placement.id}: {result['error']}")
                self.bot_util.notify_admin_failure(placement, result["error"])
                return result
        except Exception as e:
            logger.error(f"Failed to post to Telegram for placement {placement.id}: {str(e)}")
            self.bot_util.notify_admin_failure(placement, str(e))
            return {"success": False, "error": str(e)}

    def delete_from_channel(self, placement):
        """Delete a post from a Telegram channel using content_platform_id."""
        try:
            if not placement.content_platform_id:
                raise Exception("No content_platform_id available for deletion.")

            # Extract channel_id and message_id from content_platform_id (e.g., "https://t.me/c/1234567890/123")
            link_parts = placement.content_platform_id.split("/")
            if len(link_parts) < 5 or link_parts[2] != "t.me" or link_parts[3] != "c":
                raise Exception("Invalid content_platform_id format.")

            stripped_channel_id = link_parts[4]
            message_id = link_parts[5]
            channel_id = f"-100{stripped_channel_id}"

            result = self.bot_util.delete_message_from_channel(channel_id, message_id)
            if result["success"]:
                placement.status = AdPlacementStatus.STOPPED
                placement.save(update_fields=["status"])
                logger.info(f"Deleted Telegram post for placement {placement.id}, channel {placement.channel.title}")
            else:
                logger.error(f"Failed to delete Telegram post for placement {placement.id}: {result['error']}")
                self.bot_util.notify_admin_failure(placement, result["error"])
            return result
        except Exception as e:
            logger.error(f"Failed to delete Telegram post for placement {placement.id}: {str(e)}")
            self.bot_util.notify_admin_failure(placement, str(e))
            return {"success": False, "error": str(e)}

    def remove_and_repost(self, placement, new_content=None):
        """Remove an existing post and repost with new or original content, updating the model."""
        try:
            # Delete the existing post
            delete_result = self.delete_from_channel(placement)
            if not delete_result["success"]:
                logger.info(f"Deletion failed: {delete_result['error']}")
                # raise Exception(f"Deletion failed: {delete_result['error']}")

            # Repost with new or original content
            ad = placement.ad
            text_content = new_content.get("text_content", ad.text_content) if new_content else ad.text_content
            headline = new_content.get("headline", ad.headline) if new_content else ad.headline
            img_url = new_content.get("img_url", ad.img_url) if new_content else ad.img_url
            social_links = new_content.get("social_links", ad.social_links) if new_content else ad.social_links
            brand_name = new_content.get("brand_name", ad.brand_name) if new_content else ad.brand_name
            hashtags = new_content.get("hashtags", ad.hashtags if hasattr(ad, 'hashtags') else None) if new_content else (ad.hashtags if hasattr(ad, 'hashtags') else None)

            result = self.bot_util.send_message_to_channel(
                channel_id=placement.channel.channel_id,
                text_content=text_content,
                headline=headline,
                image_url=img_url,
                social_links=social_links,
                brand_name=brand_name,
                hashtags=hashtags
            )

            if result["success"]:
                placement.content_platform_id = result["link"]
                placement.status = AdPlacementStatus.RUNNING
                placement.repost_count += 1
                placement.save(update_fields=["content_platform_id", "status", "repost_count"])
                logger.info(f"Reposted to Telegram for placement {placement.id}, channel {placement.channel.title}, new link: {result['link']}")
                return {
                    "success": True,
                    "new_link": result["link"]
                }
            else:
                raise Exception(f"Repost failed: {result['error']}")
        except Exception as e:
            logger.error(f"Failed to remove and repost for placement {placement.id}: {str(e)}")
            self.bot_util.notify_admin_failure(placement, str(e))
            return {"success": False, "error": str(e)}

    def bulk_post_to_channels(self, data_dict):
        """Post to multiple Telegram channels."""
        results = {}
        for channel_id, content in data_dict.items():
            text_content = content.get("text_content", "")
            headline = content.get("headline", "")
            img_url = content.get("img")
            social_links = content.get("social_links", [])
            brand_name = content.get("brand_name")
            hashtags = content.get("hashtags")

            result = self.bot_util.send_message_to_channel(
                channel_id,
                text_content,
                headline=headline,
                image_url=img_url,
                social_links=social_links,
                brand_name=brand_name,
                hashtags=hashtags
            )
            results[channel_id] = result
        return results