import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from core.models import Campaign
User = get_user_model()

class Escrow(models.Model):
   
    class EscrowStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RELEASED = 'released', 'Released'
        CANCELLED = 'cancelled', 'Cancelled'
   
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
   
    advertiser = models.ForeignKey(User, on_delete=models.CASCADE, related_name='escrows')
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='escrows')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=EscrowStatus.choices, default=EscrowStatus.PENDING)
    assigned_creators = models.ManyToManyField(User, related_name='assigned_escrows')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)