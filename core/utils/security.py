from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib
import json

def get_fernet():
    key = settings.SECRET_KEY[:32]  # Ensure key is 32 bytes
    hashed = hashlib.sha256(key.encode()).digest()
    encoded_key = base64.urlsafe_b64encode(hashed)
    return Fernet(encoded_key)

def generate_activation_code(channel_link, user_id):
    f = get_fernet()
    data = json.dumps({
        'channel_link': channel_link,
        'user_id': str(user_id),
    })
    token = f.encrypt(data.encode()).decode()
    return token

def decrypt_activation_code(token):
    f = get_fernet()
    try:
        data = f.decrypt(token.encode()).decode()
        return json.loads(data)
    except Exception:
        return None