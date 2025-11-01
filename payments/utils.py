import secrets
import time
from django.db import transaction as db_transaction
from django.conf import settings
from decimal import Decimal, getcontext
from payments.models import Transaction

def generate_transaction_reference(prefix):
    """
    Generate a unique transaction reference with max 15 characters.
    Format: <prefix>-<4-char-base36-timestamp><6-char-random>
    Example: WDR-25A1B2C3D4 (13-15 chars depending on prefix).
    """
    # Get timestamp (YYMM, e.g., 2510 for October 2025)
    timestamp = int(time.strftime("%y%m"))
    # Convert to base36 (e.g., 2510 -> 1VY)
    timestamp_str = format(timestamp, 'X').zfill(4).upper()[:4]
    
    max_attempts = 5
    for _ in range(max_attempts):
        # Generate 6-character random alphanumeric
        random_str = ''.join(secrets.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(6))
        reference = f"{prefix}-{timestamp_str}{random_str}"
        if len(reference) <= 15 and not Transaction.objects.filter(transaction_reference=reference).exists():
            return reference
    raise ValueError("Could not generate a unique transaction reference after multiple attempts")


getcontext().prec = 28

def get_creator_share(amount):
    """
    Calculates the creator's share after applying the platform fee from Django settings.

    Args:
        amount (int, float, or Decimal): The total amount.

    Returns:
        Decimal: Creator's share after deducting platform fee.
    """
    amount = Decimal(str(amount))
    fee = Decimal(str(settings.PLATFORM_FEE)) / Decimal('100')
    creator_share = amount * (Decimal('1') - fee)
    return creator_share