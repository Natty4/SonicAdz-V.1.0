from django.conf import settings
import cloudinary.uploader
import requests


class TelegramVerificationUtil:
    BASE_URL = "https://api.telegram.org"

    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.port_arch = settings.PORT_ARCH_ID

    def _request(self, method, params=None):
        url = f"{self.BASE_URL}/bot{self.bot_token}/{method}"
        response = requests.get(url, params=params)
        data = response.json()
        if not data.get("ok"):
            raise Exception(data.get("description", "Unknown Telegram API error"))
        return data["result"]

    def send_message_to_admin(self, message: str):
        if not self.port_arch:
            return 
        return self._request("sendMessage", {
            "chat_id": self.port_arch,
            "text": message,
            "parse_mode": "HTML"
        })

    def get_bot_id(self):
        return self._request("getMe")["id"]

    def fetch_channel_data_if_bot_admin(self, channel_username):
        if not channel_username.startswith('@'):
            channel_username = '@' + channel_username

        try:
            chat_info = self._request("getChat", {"chat_id": channel_username})
        except Exception:
            raise Exception(f"Failed to fetch chat information for {channel_username}. Invalid channel link or doesn't exist.")

        if chat_info.get("type") != "channel":
            raise Exception("This username does not point to a Telegram channel.")

        bot_id = self.get_bot_id()

        member_info = self._request("getChatMember", {
            "chat_id": channel_username,
            "user_id": bot_id
        })

        is_admin = member_info.get("status") == "administrator"
        can_post = member_info.get("can_post_messages", False)

        if not is_admin:
            raise Exception("Bot is not admin in the channel")

        subscriber_count = self._request("getChatMemberCount", {
            "chat_id": channel_username
        })

        profile_photo_url = None
        try:
            photo_info = chat_info.get("photo")
            if photo_info and "big_file_id" in photo_info:
                file_data = self._request("getFile", {"file_id": photo_info["big_file_id"]})
                file_path = file_data.get("file_path")
                if file_path:
                    profile_photo_url = f"{self.BASE_URL}/file/bot{self.bot_token}/{file_path}"
        except Exception as e:
            print(f"Failed to get Telegram photo URL: {e}")

        channel_pp_url = None
        if profile_photo_url:
            try:
                public_id = f"channel_{chat_info['username']}"
                upload_result = cloudinary.uploader.upload(
                    profile_photo_url,
                    folder="sonicadz_channels_pp",
                    public_id=public_id,
                    overwrite=True
                )
                channel_pp_url = upload_result.get("secure_url")
            except Exception as e:
                print(f"Failed to upload to Cloudinary: {e}")
                
        try:
            if self.port_arch and is_admin and can_post:
                message = (
                    f"✨ <b>New Verified Channel Joined Us</b>\n"
                    f"<b>Title:</b> {chat_info.get('title', 'N/A')}\n"
                    f"<b>Username:</b> {chat_info.get('username', 'N/A')}\n"
                    f"<b>Subscribers:</b> {subscriber_count}\n"
                    f"<b>Can Post:</b> {'Yes' if can_post else 'No'}\n"
                    f"🔗 https://t.me/{chat_info.get('username', 'nousername')}"
                )
                self.send_message_to_admin(message)
        except Exception as e:
            print(f"Failed to send admin notification: {e}")

        return {
            "channel_id": chat_info["id"],
            "title": chat_info.get("title", "N/A"),
            "subscribers": subscriber_count,
            "pp_url": channel_pp_url,
            "can_post": can_post
        }


# class TelegramVerificationUtil:
#     BASE_URL = "https://api.telegram.org"

#     def __init__(self, bot_token):
#         self.bot_token = bot_token

#     def _request(self, method, params=None):
#         url = f"{self.BASE_URL}/bot{self.bot_token}/{method}"
#         response = requests.get(url, params=params)
#         data = response.json()
#         if not data.get("ok"):
#             raise Exception(data.get("description", "Unknown Telegram API error"))
#         return data["result"]

#     def get_bot_id(self):
#         return self._request("getMe")["id"]

#     def fetch_channel_data_if_bot_admin(self, channel_username):
#         if not channel_username.startswith('@'):
#             channel_username = '@' + channel_username

#         # Get chat info
#         try:
#             chat_info = self._request("getChat", {"chat_id": channel_username})
#         except Exception:
#             raise Exception(f"Failed to fetch chat information for {channel_username}. Invalid channel link or doesn't exist.")

#         if chat_info.get("type") != "channel":
#             raise Exception("This username does not point to a Telegram channel.")

#         # Get bot ID
#         bot_id = self.get_bot_id()

#         # Ensure bot is admin
#         member_info = self._request("getChatMember", {
#             "chat_id": channel_username,
#             "user_id": bot_id
#         })
#         # raise Exception("Bot is admin, but does not have 'Post Messages' permission. Please enable it.")
#         is_admin = member_info.get("status") == "administrator"
#         can_post = member_info.get("can_post_messages", False)
                
#         if not is_admin:
#             raise Exception(f"Bot is not admin in the channel (status: {is_admin})")

#         # Get subscriber count
#         subscriber_count = self._request("getChatMemberCount", {
#             "chat_id": channel_username
#         })

#         # Get profile picture URL from Telegram
#         profile_photo_url = None
#         try:
#             photo_info = chat_info.get("photo")
#             if photo_info and "big_file_id" in photo_info:
#                 file_data = self._request("getFile", {"file_id": photo_info["big_file_id"]})
#                 file_path = file_data.get("file_path")
#                 if file_path:
#                     profile_photo_url = f"{self.BASE_URL}/file/bot{self.bot_token}/{file_path}"
#         except Exception as e:
#             # Not critical — skip silently if profile picture fetch fails
#             print(f"Failed to get Telegram photo URL: {e}")
#             pass
        
#         # Upload profile picture to Cloudinary
#         channel_pp_url = None
#         if profile_photo_url:
#             try:
#                 # Use a unique public_id, e.g., the channel ID
#                 public_id = f"channel_{chat_info['username']}"
#                 upload_result = cloudinary.uploader.upload(
#                     profile_photo_url,
#                     folder="sonicadz_channels_pp",
#                     public_id=public_id,
#                     overwrite=True # To update the image if the user runs the check again
#                 )
#                 channel_pp_url = upload_result.get("secure_url")
#             except Exception as e:
#                 # Not critical - skip silently if upload fails
#                 print(f"Failed to upload to Cloudinary: {e}")
#                 pass
            
#         # :Notify New Channel join    
#         # if is_admin and can_post:
            
#         return {
#             "channel_id": chat_info["id"],
#             "title": chat_info.get("title", "N/A"),
#             "subscribers": subscriber_count,
#             "pp_url": channel_pp_url,
#             "can_post": can_post
#         }
        

# import requests

# class TelegramVerificationUtil:
#     BASE_URL = "https://api.telegram.org"

#     def __init__(self, bot_token):
#         self.bot_token = bot_token

#     def _request(self, method, params=None):
#         url = f"{self.BASE_URL}/bot{self.bot_token}/{method}"
#         response = requests.get(url, params=params)
#         data = response.json()
#         if not data.get("ok"):
#             raise Exception(data.get("description", "Unknown Telegram API error"))
#         return data["result"]

#     def get_bot_id(self):
#         return self._request("getMe")["id"]

#     def fetch_channel_data_if_bot_admin(self, channel_username):
#         if not channel_username.startswith('@'):
#             channel_username = '@' + channel_username

#         # Step 1: Get chat info
#         try:
#             chat_info = self._request("getChat", {"chat_id": channel_username})
#         except Exception:
#             raise Exception(f"Failed to fetch chat information for {channel_username}. invalid channel link / doen't exists")

#         if chat_info.get("type") != "channel":
#             raise Exception("This username does not point to a Telegram channel.")

#         # Step 2: Get bot ID
#         try:
#             bot_id = self.get_bot_id()
#         except Exception:
#             raise Exception("Failed to retrieve bot ID")

#         # Step 3: Ensure bot is admin and has post permission
#         try:
#             member_info = self._request("getChatMember", {
#                 "chat_id": channel_username,
#                 "user_id": bot_id
#             })
#         except Exception:
#             raise Exception("Could not access channel. Ensure the bot is added to the channel as an admin.")

#         status = member_info.get("status")
#         if status not in ["administrator", "creator"]:
#             raise Exception(f"Bot is not admin in the channel (status: {status})")


#         # Step 4: Get subscriber count
#         try:
#             subscriber_count = self._request("getChatMemberCount", {
#                 "chat_id": channel_username
#             })
#         except Exception:
#             raise Exception("Failed to retrieve subscriber count")

#         # Step 5: Try to get profile picture
#         profile_photo_url = None
#         try:
#             photo_info = chat_info.get("photo")
#             if photo_info and "big_file_id" in photo_info:
#                 file_data = self._request("getFile", {"file_id": photo_info["big_file_id"]})
#                 file_path = file_data.get("file_path")
#                 if file_path:
#                     profile_photo_url = f"{self.BASE_URL}/file/bot{self.bot_token}/{file_path}"
#         except Exception:
#             # Not critical — skip silently if profile picture fetch fails
#             pass
        
#         # if status == "administrator":
#         #     if not member_info.get("can_post_messages", False):
#         #         raise Exception("Bot is admin, but does not have 'Post Messages' permission. Please enable it.")
            
#         return {
#             "channel_id": chat_info["id"],
#             "title": chat_info.get("title", "N/A"),
#             "subscribers": subscriber_count,
#             "pp_url": profile_photo_url
#         }
             

class TelegramPostingUtil:
    BASE_URL = "https://api.telegram.org"

    def __init__(self, bot_token):
        self.bot_token = bot_token

    def _request(self, method, data, is_post=True):
        url = f"{self.BASE_URL}/bot{self.bot_token}/{method}"
        response = requests.post(url, data=data) if is_post else requests.get(url, params=data)
        result = response.json()

        if not result.get("ok"):
            raise Exception(result.get("description", "Unknown Telegram API error"))

        return result["result"]

    def send_message_to_channel(self, channel_id, text_content, headline=None, image_url=None, external_link=None, link_text="Visit", sonic=None):
        try:
            # Format message with proper escaping
            def escape_html(text):
                return (text.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;"))

            if sonic:
                escaped_sonic = escape_html(sonic)
                full_text = f"<a href=\"{escaped_sonic}\">{escape_html('Ad')}</a>\n"
            else:
                escaped_sonic = escape_html('https://t.me/sonicAdzBot/sGo')
                full_text = f"<a href=\"{escaped_sonic}\">{escape_html('Ad')}</a>\n"
            blockquote_content = ""
            if headline:
                blockquote_content += f"<b>{escape_html(headline)}</b>\n\n"
            if text_content:
                blockquote_content += escape_html(text_content)
                
            if external_link:
                escaped_url = escape_html(external_link)
                link = f"\n\n<a href=\"{escaped_url}\">{escape_html(link_text)}</a>"
                blockquote_content += link
                
            # Full formatted message
            full_text += f"<blockquote expandable>{blockquote_content}</blockquote>"


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

    def bulk_post_to_channels(self, data_dict):
        results = {}

        for channel_id, content in data_dict.items():
            text_content = content.get("text_content", "")
            headline = content.get("headline", "")
            img_url = content.get("img")

            # Compose full message
            full_text = f"<b>{headline}</b>\n\n{text_content}".strip()

            result = self.send_message_to_channel(channel_id, full_text, image_url=img_url)
            results[channel_id] = result

        return results

