from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)

def send_telegram_notification(chat_id, text):
    url = f"https://api.telegram.org/bot{settings.BOT_SECRET_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown', 
    }
    try:
        response = requests.post(url, data=payload, timeout=5)
        response.raise_for_status()
        logger.info(f"Telegram message sent to {chat_id}")
    except requests.RequestException as e:
        logger.error(f"Telegram send error: {e}")
