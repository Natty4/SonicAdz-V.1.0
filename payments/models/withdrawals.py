import uuid
from django.db import models
from payments.models import UserPaymentMethod
    
class WithdrawalRequest(models.Model):
    class RequestStatus(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        COMPLETED = 'completed', 'Completed'
        REJECTED = 'rejected', 'Rejected'
        PENDING = 'pending', 'Pending'
       
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    user_payment_method = models.ForeignKey(
        UserPaymentMethod,
        on_delete=models.SET_NULL,
        null=True)
    amount = models.DecimalField(
        max_digits=6,
        decimal_places=2)
    reference = models.CharField(
        max_length=100)
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f"Withdrawal {self.id} for {self.user_payment_method.user}"

