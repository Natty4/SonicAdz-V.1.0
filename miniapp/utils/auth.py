import json
import logging
import urllib.parse
import hmac
import hashlib
import time
import uuid
from datetime import datetime
from typing import Dict, Optional
from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.contrib.auth import login, update_session_auth_hash
from django.http import JsonResponse
from users.models import TelegramProfile, UserType
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model() 

logger = logging.getLogger(__name__)

class TelegramAuthHelper:
    @staticmethod
    def parse_init_data(init_data: str) -> Dict[str, str]:
        """Parse Telegram initData into a dictionary."""
        try:
            return dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        except Exception as e:
            logger.error(f"Error parsing init_data: {str(e)}")
            return {}

    @staticmethod
    def is_valid_telegram_init_data(init_data: str, bot_token: str) -> bool:
        """Verify Telegram WebApp initData authenticity using HMAC-SHA256."""
        if not init_data or not bot_token:
            logger.warning("Empty init_data or bot_token provided")
            return False

        try:
            parsed = TelegramAuthHelper.parse_init_data(init_data)
            if not parsed:
                return False

            # Extract and remove hash for validation
            received_hash = parsed.pop('hash', None)
            if not received_hash:
                logger.warning("Missing hash in init_data")
                return False

            auth_date = int(parsed.get("auth_date", "0"))
            if abs(time.time() - auth_date) > 86400:  # 24 hours
                logger.warning("Expired Telegram login")
                return False
            
            # Prepare data check string
            data_check_string = '\n'.join(
                f"{k}={v}" for k, v in sorted(parsed.items())
            )

            # Compute secret key
            secret_key = hmac.new(
                b"WebAppData",
                msg=bot_token.encode(),
                digestmod=hashlib.sha256
            ).digest()

            # Compute expected hash
            expected_hash = hmac.new(
                secret_key,
                msg=data_check_string.encode(),
                digestmod=hashlib.sha256
            ).hexdigest()

            # Compare hashes securely
            return hmac.compare_digest(expected_hash, received_hash)

        except Exception as e:
            logger.error(f"Error validating init_data: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def extract_telegram_user_data(init_data: str) -> Optional[Dict]:
        try:
            parsed = TelegramAuthHelper.parse_init_data(init_data)
            user_json = parsed.get("user")
            if not user_json:
                return None

            user_data = json.loads(user_json)
            if not user_data.get("id"):
                logger.warning("Missing Telegram user ID in init_data")
                return None

            return {
                "id": user_data["id"],
                "username": user_data.get("username"),
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "language_code": user_data.get("language_code"),
                "photo_url": user_data.get("photo_url"),
                "is_premium": user_data.get("is_premium", False),
                "auth_date": user_data.get("auth_date", ""),
            }

        except Exception as e:
            logger.error(f"Failed to parse Telegram user data: {e}")
            return None

    @staticmethod
    def process_telegram_auth(request, data: str) -> JsonResponse:
        """Handle the complete Telegram authentication flow."""
        if not TelegramAuthHelper.is_valid_telegram_init_data(data['init_data'], settings.BOT_SECRET_TOKEN):
            logger.warning(f"Invalid Telegram auth attempt from IP: {request.META.get('REMOTE_ADDR')}")
            return JsonResponse({"error": "Invalid Telegram authentication"}, status=403)

        user_data = TelegramAuthHelper.extract_telegram_user_data(data['init_data'])
        if not user_data or not user_data.get('id'):
            return JsonResponse({"error": "Invalid Telegram user data"}, status=400)

        try:
            tg_id = user_data['id']
            telegram_profile = TelegramProfile.objects.select_related("user").filter(tg_id=tg_id).first()

            if telegram_profile:
                # User exists - log them in
                user = telegram_profile.user
                # telegram_profile.update_field(photo_url=user_data['photo_url'])
                # telegram_profile.photo_url = user_data.get('photo_url')
                # telegram_profile.save(update_fields=['photo_url'])
                login(request, user)
                request.session['auth_source'] = 'telegram'
                update_session_auth_hash(request, user)

                return JsonResponse({
                    "success": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "user_type": user.user_type,
                        "is_authenticated": True
                    },
                    "redirect_url": "/main/" 
                })

            # New user flow
            with transaction.atomic():
                user, created = User.objects.get_or_create(
                    phone_number=data['phone_number'],
                    defaults={
                        "user_type": UserType.CREATOR,
                        "username": user_data.get("username") or f"user_{uuid.uuid4().hex[:6]}",
                        "first_name": data.get("first_name", user_data.get("first_name", "")),
                        "last_name": data.get("last_name", user_data.get("last_name", "")),
                        "email": data.get("email", ""),

                    }
                )

                TelegramProfile.objects.create(
                    tg_id=tg_id,
                    user=user,
                    username=user_data.get("username"),
                    first_name=user_data.get("first_name", ""),
                    last_name=user_data.get("last_name", ""),
                    language_code=user_data.get("language_code"),
                    photo_url=user_data.get("photo_url"),
                    is_premium=user_data.get("is_premium", False),
                    auth_date=datetime.fromtimestamp(int(user_data["auth_date"])) if user_data.get("auth_date") else timezone.now(),
                )

                login(request, user)
                request.session['auth_source'] = 'telegram'
                update_session_auth_hash(request, user)

                return JsonResponse({
                    "success": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "user_type": user.user_type,
                        "is_authenticated": True
                    },
                    "redirect_url": "/main/" 
                })

        except IntegrityError as e:
            logger.error(f"Database error during Telegram auth: {str(e)}")
            return JsonResponse({"error": "Account conflict - please contact support"}, status=409)
        except Exception as e:
            logger.error(f"Unexpected Telegram auth error: {str(e)}", exc_info=True)
            return JsonResponse({"error": "Authentication service unavailable"}, status=500)