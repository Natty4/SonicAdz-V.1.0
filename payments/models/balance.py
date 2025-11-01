import uuid
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

class BalanceType(models.TextChoices):
    CREATOR = 'creator', 'Creator'
    ADVERTISER = 'advertiser', 'Advertiser'

class Balance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='balance')
    type = models.CharField(max_length=20, choices=BalanceType.choices)
    available = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    escrow = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pending_withdrawals = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total(self):
        return self.available + self.escrow + self.pending_withdrawals

TRANSACTION_TYPES = [
    ('deposit', 'Deposit'),
    ('withdraw', 'Withdraw'),
    ('credit', 'Credit'),
    ('debit', 'Debit'),
    ('spend', 'Spend'),
    ('earning', 'Earning'),
]

class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    balance = models.ForeignKey(Balance, on_delete=models.CASCADE, related_name='transactions')  # New ForeignKey
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    sub_balance = models.CharField(
        max_length=20,
        choices=[('available', 'Available'), ('escrow', 'Escrow'), ('pending_withdrawals', 'Pending Withdrawals')],
        default='available'
    )
    after_balance = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_reference = models.CharField(max_length=100, unique=True)  # Ensure unique=True
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type}"