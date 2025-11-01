import random
import requests
from typing import Tuple
from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.conf import settings

OTP_TTL_SECONDS = 300  # 5 minutes
RESEND_COOLDOWN_SECONDS = 60  # 1 minute

def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_via_telegram(tg_user_id, otp_code):
    message = (
        f"<b>⚡ Your SonicAdz OTP Code</b> "
        f"<code>{otp_code}</code>\n\n"
        f"This code will <b>expire in 5 minutes</b>.\n"
        # f"Do not share this code with anyone."
    )

    url = f"https://api.telegram.org/bot{settings.BOT_SECRET_TOKEN}/sendMessage"
    payload = {
        "chat_id": tg_user_id,
        "text": message,
        "parse_mode": "HTML"
    }

    response = requests.post(url, json=payload)
    return response.ok


def is_otp_cooldown_active(session) -> bool:
    """Returns True if OTP was sent recently (within cooldown)."""
    last_sent_str = session.get("otp_last_sent")
    if not last_sent_str:
        return False

    try:
        last_sent = timezone.datetime.fromisoformat(last_sent_str)
        return timezone.now() - last_sent < timedelta(seconds=RESEND_COOLDOWN_SECONDS)
    except Exception:
        return False


def store_otp_in_session(session, otp_code: str, user_id: int):
    session["otp_code"] = otp_code
    session["otp_expiry"] = (timezone.now() + timedelta(seconds=OTP_TTL_SECONDS)).isoformat()
    session["otp_last_sent"] = timezone.now().isoformat()
    session["otp_user_id"] = user_id



def is_otp_valid(session, user_input: str) -> Tuple[bool, str]:
    """Validates OTP input against session values. Returns (success, error_message)."""
    session_code = session.get("otp_code")
    expiry_str = session.get("otp_expiry")
    user_id = session.get("otp_user_id")

    if not session_code or not expiry_str or not user_id:
        return False, "OTP session expired or invalid"

    expiry = parse_datetime(expiry_str)
    if not expiry or timezone.now() > expiry:
        return False, "OTP has expired"

    if user_input != session_code:
        return False, "Incorrect OTP"

    return True, ""


def clear_otp_session_data(session):
    for key in ["otp_code", "otp_expiry", "otp_user_id", "otp_last_sent", "otp_tg_id"]:
        session.pop(key, None)