import requests
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

class TelegramBotUtil:
    BASE_URL = "https://api.telegram.org"

    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.admin_chat_id = getattr(settings, 'ADMIN_USER', os.getenv('ADMIN_USER'))

    def _request(self, method, data, is_post=True):
        """Make a request to the Telegram API."""
        if not self.bot_token:
            raise ValueError("Telegram bot token is not configured.")
        
        url = f"{self.BASE_URL}/bot{self.bot_token}/{method}"
        try:
            response = requests.post(url, data=data) if is_post else requests.get(url, params=data)
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                raise Exception(result.get("description", "Unknown Telegram API error"))
            return result["result"]
        except Exception as e:
            logger.error(f"Telegram API request failed for {method}: {str(e)}")
            raise

    def format_message(self, text_content, headline=None, sonic=None, social_links=None, brand_name=None, hashtags=None):
        """Format a Telegram message with the specified structure."""
        def escape_html(text):
            return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") if text else "")

        full_text = ""
        if sonic:
            escaped_sonic = escape_html(sonic)
            blockquote_content = f"<a href=\"{escaped_sonic}\">{escape_html('Ad')}</a> "
        else:
            escaped_sonic = escape_html('https://t.me/sonicAdzBot/sGo')
            blockquote_content = f"<a href=\"{escaped_sonic}\">{escape_html('Ad')}</a> "

        if headline:
            blockquote_content += f"<b>{escape_html(headline)}</b>\n\n"
        if text_content:
            blockquote_content += escape_html(text_content)

        # Add social links, brand name, and hashtags (if provided) on separate lines
        footer_parts = []
        if social_links:
            social_links_parts = []
            for link in social_links:
                platform = link.get("platform", "")
                url = link.get("url", "")
                if platform and url:
                    escaped_platform = escape_html(platform)
                    escaped_url = escape_html(url)
                    social_links_parts.append(f"<a href=\"{escaped_url}\">{escaped_platform}</a>")
            social_links_str = " | ".join(social_links_parts)
            if social_links_str:
                footer_parts.append(social_links_str)
        if brand_name:
            footer_parts.append(escape_html(brand_name))
        if hashtags:
            footer_parts.append(escape_html(hashtags))
        else:
            footer_parts.append(escape_html("#SonicAdz #TelegramAds #Ethiopia"))
        if footer_parts:
            blockquote_content += "\n\n" + "\n".join(footer_parts)

        full_text += f"<blockquote expandable>{blockquote_content}</blockquote>"
        return full_text

    def send_message_to_channel(self, channel_id, text_content, headline=None, image_url=None, sonic=None, social_links=None, brand_name=None, hashtags=None):
        """Send a message or photo to a Telegram channel."""
        try:
            full_text = self.format_message(
                text_content,
                headline=headline,
                sonic=sonic,
                social_links=social_links,
                brand_name=brand_name,
                hashtags=hashtags
            )
            payload = {
                "chat_id": channel_id,
                "parse_mode": "HTML"
            }

            if image_url:
                payload.update({
                    "photo": image_url,
                    "caption": full_text,
                    "show_caption_above_media": True
                })
                result = self._request("sendPhoto", payload)
            else:
                payload.update({"text": full_text})
                result = self._request("sendMessage", payload)

            return {
                "success": True,
                "message_id": result["message_id"],
                "chat_id": result["chat"]["id"],
                "link": f"https://t.me/c/{str(result['chat']['id']).lstrip('-100')}/{result['message_id']}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def delete_message_from_channel(self, channel_id, message_id):
        """Delete a message from a Telegram channel."""
        try:
            payload = {
                "chat_id": channel_id,
                "message_id": message_id
            }
            result = self._request("deleteMessage", payload)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def notify_admin_failure(self, placement, error_msg):
        """Notify the admin of a failure via Telegram."""
        if not self.admin_chat_id:
            logger.warning("Admin Telegram chat ID not configured; skipping admin notification.")
            return

        try:
            message = (
                f"🚨 <b>Telegram Posting Failed!</b>\n\n"
                f"<b>Placement ID:</b> <code>{placement.id}</code>\n"
                f"<b>Campaign:</b> {placement.ad.campaign.name}\n"
                f"<b>Ad:</b> {placement.ad.headline}\n"
                f"<b>Channel:</b> {placement.channel.title}\n"
                f"<b>Error:</b> {error_msg}"
            )
            payload = {
                "chat_id": self.admin_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            self._request("sendMessage", payload)
            logger.info(f"Admin notified about Telegram failure for placement {placement.id}")
        except Exception as e:
            logger.error(f"Failed to notify admin via Telegram: {str(e)}")












































# import requests
# import logging
# import os

# from django.conf import settings

# logger = logging.getLogger(__name__)

# class TelegramPostingUtil:
#     BASE_URL = "https://api.telegram.org"

#     def __init__(self, bot_token):
#         self.bot_token = bot_token
#         self.admin_chat_id = getattr(settings, 'ADMIN_USER', os.getenv('ADMIN_USER'))

#     def _request(self, method, data, is_post=True):
#         url = f"{self.BASE_URL}/bot{self.bot_token}/{method}"
#         response = requests.post(url, data=data) if is_post else requests.get(url, params=data)
#         result = response.json()

#         if not result.get("ok"):
#             raise Exception(result.get("description", "Unknown Telegram API error"))

#         return result["result"]

#     def send_message_to_channel(self, channel_id, text_content, headline=None, image_url=None, sonic=None, social_links=None, brand_name=None, hashtags=None):
#         try:
#             # Format message with proper escaping
#             def escape_html(text):
#                 return (text.replace("&", "&amp;")
#                             .replace("<", "&lt;")
#                             .replace(">", "&gt;") if text else "")

#             full_text = ""
#             if sonic:
#                 escaped_sonic = escape_html(sonic)
#                 blockquote_content = f"<a href=\"{escaped_sonic}\">{escape_html('Ad')}</a> "
#             else:
#                 escaped_sonic = escape_html('https://t.me/sonicAdzBot/sGo')
#                 blockquote_content = f"<a href=\"{escaped_sonic}\">{escape_html('Ad')}</a> "

#             if headline:
#                 blockquote_content += f"<b>{escape_html(headline)}</b>\n\n"
#             if text_content:
#                 blockquote_content += escape_html(text_content)

#             # Add social links, brand name, and hashtags (if provided) on separate lines
#             footer_parts = []
#             if social_links:
#                 # Format social links as clickable "X | TikTok | Instagram..."
#                 social_links_parts = []
#                 for link in social_links:
#                     platform = link.get("platform", "")
#                     url = link.get("url", "")
#                     if platform and url:
#                         escaped_platform = escape_html(platform)
#                         escaped_url = escape_html(url)
#                         social_links_parts.append(f"<a href=\"{escaped_url}\">{escaped_platform}</a>")
#                 social_links_str = " | ".join(social_links_parts)
#                 if social_links_str:
#                     footer_parts.append(social_links_str)
#             if brand_name:
#                 footer_parts.append(escape_html(brand_name))
#             if hashtags:
#                 footer_parts.append(escape_html(hashtags))

#             if footer_parts:
#                 blockquote_content += "\n\n" + "\n".join(footer_parts)

#             # Full formatted message
#             full_text += f"<blockquote expandable>{blockquote_content}</blockquote>"

#             payload = {
#                 "chat_id": channel_id,
#                 "parse_mode": "HTML"
#             }

#             if image_url:
#                 payload.update({
#                     "photo": image_url,
#                     "caption": full_text,
#                     "show_caption_above_media": True
#                 })
#                 result = self._request("sendPhoto", payload)
#             else:
#                 payload.update({"text": full_text})
#                 result = self._request("sendMessage", payload)

#             return {
#                 "success": True,
#                 "message_id": result["message_id"],
#                 "chat_id": result["chat"]["id"],
#                 "link": f"https://t.me/c/{str(result['chat']['id']).lstrip('-100')}/{result['message_id']}"
#             }

#         except Exception as e:
#             return {
#                 "success": False,
#                 "error": str(e)
#             }

#     def delete_message_from_channel(self, channel_id, message_id):
#         try:
#             payload = {
#                 "chat_id": channel_id,
#                 "message_id": message_id
#             }

#             result = self._request("deleteMessage", payload)
#             return {
#                 "success": True,
#                 "result": result
#             }

#         except Exception as e:
#             return {
#                 "success": False,
#                 "error": str(e)
#             }

#     def remove_and_repost(self, placement, new_content=None):
#         try:
#             # Parse the content_platform_id to extract channel_id and message_id
#             if not placement.content_platform_id:
#                 raise Exception("No content_platform_id available for deletion.")

#             # Extract message_id and channel_id from link (e.g., "https://t.me/c/1234567890/123")
#             link_parts = placement.content_platform_id.split("/")
#             if len(link_parts) < 5 or link_parts[2] != "t.me" or link_parts[3] != "c":
#                 raise Exception("Invalid content_platform_id format.")

#             stripped_channel_id = link_parts[4]
#             message_id = link_parts[5]

#             # Reconstruct full channel_id as "-100" + stripped_channel_id
#             channel_id = f"-100{stripped_channel_id}"

#             # Delete the existing message
#             delete_result = self.delete_message_from_channel(channel_id, message_id)
#             if not delete_result["success"]:
#                 raise Exception(f"Deletion failed: {delete_result['error']}")

#             # Repost with new content or original content
#             ad = placement.ad
#             text_content = new_content.get("text_content", ad.text_content) if new_content else ad.text_content
#             headline = new_content.get("headline", ad.headline) if new_content else ad.headline
#             img_url = new_content.get("img_url", ad.img_url) if new_content else ad.img_url
#             social_links = new_content.get("social_links", ad.social_links) if new_content else ad.social_links
#             brand_name = new_content.get("brand_name", ad.brand_name) if new_content else ad.brand_name
#             hashtags = new_content.get("hashtags", "") if new_content else ""

#             post_result = self.send_message_to_channel(
#                 channel_id=channel_id,
#                 text_content=text_content,
#                 headline=headline,
#                 image_url=img_url,
#                 social_links=social_links,
#                 brand_name=brand_name,
#                 hashtags=hashtags
#             )

#             if post_result["success"]:
#                 # Update the model with the new content_platform_id
#                 placement.content_platform_id = post_result["link"]
#                 placement.save(update_fields=["content_platform_id"])
#                 return {
#                     "success": True,
#                     "new_link": post_result["link"]
#                 }
#             else:
#                 raise Exception(f"Repost failed: {post_result['error']}")

#         except Exception as e:
#             return {
#                 "success": False,
#                 "error": str(e)
#             }

#     def bulk_post_to_channels(self, data_dict):
#         results = {}

#         for channel_id, content in data_dict.items():
#             text_content = content.get("text_content", "")
#             headline = content.get("headline", "")
#             img_url = content.get("img")
#             social_links = content.get("social_links", [])
#             brand_name = content.get("brand_name")
#             hashtags = content.get("hashtags")

#             result = self.send_message_to_channel(
#                 channel_id,
#                 text_content,
#                 headline=headline,
#                 image_url=img_url,
#                 social_links=social_links,
#                 brand_name=brand_name,
#                 hashtags=hashtags
#             )
#             results[channel_id] = result

#         return results

#     def notify_admin_failure(self, placement, error_msg):
#         if not self.admin_chat_id:
#             logger.warning("Admin Telegram chat ID not configured; skipping admin notification.")
#             return

#         try:
#             message = (
#                 f"🚨 <b>Telegram Posting Failed!</b>\n\n"
#                 f"<b>Placement ID:</b> <code>{placement.id}</code>\n"
#                 f"<b>Campaign:</b> {placement.ad.campaign.name}\n"
#                 f"<b>Ad:</b> {placement.ad.headline}\n"
#                 f"<b>Channel:</b> {placement.channel.title}\n"
#                 f"<b>Error:</b> {error_msg}"
#             )

#             payload = {
#                 "chat_id": self.admin_chat_id,
#                 "text": message,
#                 "parse_mode": "HTML"
#             }

#             self._request("sendMessage", payload)
#             logger.info(f"Admin notified about Telegram failure for placement {placement.id}")

#         except Exception as e:
#             logger.error(f"Failed to notify admin via Telegram: {str(e)}")












































# import requests
# import logging
# import os

# from django.conf import settings

# logger = logging.getLogger(__name__)


# class TelegramPostingUtil:
#     BASE_URL = "https://api.telegram.org"

#     def __init__(self, bot_token):
#         self.bot_token = bot_token
#         self.admin_chat_id = getattr(settings, 'ADMIN_USER', os.getenv('ADMIN_USER'))

#     def _request(self, method, data, is_post=True):
#         url = f"{self.BASE_URL}/bot{self.bot_token}/{method}"
#         response = requests.post(url, data=data) if is_post else requests.get(url, params=data)
#         result = response.json()

#         if not result.get("ok"):
#             raise Exception(result.get("description", "Unknown Telegram API error"))

#         return result["result"]

#     # def _upload_and_send_image(self, chat_id, image_url, caption):
#     #     try:
#     #         response = requests.get(image_url, stream=True, timeout=10)
#     #         response.raise_for_status()

#     #         files = {
#     #             'photo': ('image.jpg', response.content)
#     #         }
#     #         data = {
#     #             'chat_id': chat_id,
#     #             'caption': caption,
#     #             'parse_mode': 'HTML'
#     #         }
#     #         url = f"{self.BASE_URL}/bot{self.bot_token}/sendPhoto"
#     #         telegram_response = requests.post(url, data=data, files=files)
#     #         result = telegram_response.json()

#     #         if not result.get("ok"):
#     #             raise Exception(result.get("description", "Unknown Telegram API error"))

#     #         return result["result"]
#     #     except Exception as e:
#     #         raise Exception(f"Image upload failed: {str(e)}")

#     def send_message_to_channel(self, channel_id, text_content, headline=None, image_url=None, external_link=None, link_text="Visit", sonic=None):
#         try:
#             # Format message with proper escaping
#             def escape_html(text):
#                 return (text.replace("&", "&amp;")
#                             .replace("<", "&lt;")
#                             .replace(">", "&gt;"))
#             full_text = ""
#             if sonic:
#                 escaped_sonic = escape_html(sonic)
#                 blockquote_content = f"<a href=\"{escaped_sonic}\">{escape_html('Ad')}</a> "
#             else:
#                 escaped_sonic = escape_html('https://t.me/sonicAdzBot/sGo')
#                 blockquote_content = f"<a href=\"{escaped_sonic}\">{escape_html('Ad')}</a> "

            
#             if headline:
#                 blockquote_content += f"<b>{escape_html(headline)}</b>\n\n"
#             if text_content:
#                 blockquote_content += escape_html(text_content)

#             if external_link:
#                 escaped_url = escape_html(external_link)
#                 link = f"\n\n<a href=\"{escaped_url}\">{escape_html(link_text)}</a>"
#                 blockquote_content += link

#             # Full formatted message
#             full_text += f"<blockquote expandable>{blockquote_content}</blockquote>"

#             payload = {
#                 "chat_id": channel_id,
#                 "parse_mode": "HTML"
#             }

#             if image_url:
#                 payload.update({
#                     "photo": image_url,
#                     "caption": full_text,
#                     "show_caption_above_media": True
#                 })
#                 result = self._request("sendPhoto", payload)
                
#             else:
#                 payload.update({"text": full_text})
#                 result = self._request("sendMessage", payload)

#             return {
#                 "success": True,
#                 "message_id": result["message_id"],
#                 "chat_id": result["chat"]["id"],
#                 "link": f"https://t.me/c/{str(result['chat']['id']).lstrip('-100')}/{result['message_id']}"
#             }

#         except Exception as e:
#             return {
#                 "success": False,
#                 "error": str(e)
#             }

#     def bulk_post_to_channels(self, data_dict):
#         results = {}

#         for channel_id, content in data_dict.items():
#             text_content = content.get("text_content", "")
#             headline = content.get("headline", "")
#             img_url = content.get("img")

#             # Compose full message
#             full_text = f"<b>{headline}</b>\n\n{text_content}".strip()

#             result = self.send_message_to_channel(channel_id, full_text, image_url=img_url)
#             results[channel_id] = result

#         return results

#     def notify_admin_failure(self, placement, error_msg):
#         if not self.admin_chat_id:
#             logger.warning("Admin Telegram chat ID not configured; skipping admin notification.")
#             return

#         try:
#             message = (
#                 f"🚨 <b>Telegram Posting Failed!</b>\n\n"
#                 f"<b>Placement ID:</b> <code>{placement.id}</code>\n"
#                 f"<b>Campaign:</b> {placement.ad.campaign.name}\n"
#                 f"<b>Ad:</b> {placement.ad.headline}\n"
#                 f"<b>Channel:</b> {placement.channel.title}\n"
#                 f"<b>Error:</b> {error_msg}"
#             )

#             payload = {
#                 "chat_id": self.admin_chat_id,
#                 "text": message,
#                 "parse_mode": "HTML"
#             }

#             self._request("sendMessage", payload)
#             logger.info(f"Admin notified about Telegram failure for placement {placement.id}")

#         except Exception as e:
#             logger.error(f"Failed to notify admin via Telegram: {str(e)}")

