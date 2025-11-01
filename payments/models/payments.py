# import uuid

# from decimal import Decimal
# from django.db import models
# from django.contrib.auth import get_user_model
# from phonenumber_field.modelfields import PhoneNumberField

# User = get_user_model()

# class PaymentMethodType(models.Model):
#     class MethodCategory(models.TextChoices):
#         BANK = 'bank', 'Bank'
#         WALLET = 'wallet', 'Mobile Wallet'

#     id = models.UUIDField(
#         primary_key=True, 
#         default=uuid.uuid4, 
#         editable=False)
#     name = models.CharField(
#         max_length=100, 
#         unique=True)  # e.g. "Chase", "M-Pesa"
#     short_name = models.CharField(
#         max_length=10, 
#         null=True, 
#         blank=True)
#     category = models.CharField(
#         max_length=20, 
#         choices=MethodCategory.choices)
#     logo = models.CharField(
#         max_length=255, 
#         null=True, 
#         blank=True, 
#         help_text="Optional logo (PNG, SVG, etc.)")
#     is_active = models.BooleanField(default=True)

#     def __str__(self):
#         return f"{self.name} ({self.get_category_display()})"


# class UserPaymentMethod(models.Model):
#     class Status(models.TextChoices):
#         PENDING = 'pending', 'Pending'
#         VERIFIED = 'verified', 'Verified'
#         REJECTED = 'rejected', 'Rejected'

#     id = models.UUIDField(
#         primary_key=True, 
#         default=uuid.uuid4, 
#         editable=False)
#     user = models.ForeignKey(
#         User, 
#         on_delete=models.SET_NULL, 
#         null=True, blank=True, 
#         related_name='payment_methods')
#     payment_method_type = models.ForeignKey(
#         PaymentMethodType, 
#         on_delete=models.CASCADE, 
#         related_name='user_payment_methods')
#     account_name = models.CharField(max_length=255)
#     account_number = models.CharField(max_length=50, blank=True, null=True)
#     phone_number = PhoneNumberField(null=True, blank=True)
#     status = models.CharField(
#         max_length=10, 
#         choices=Status.choices, 
#         default=Status.PENDING)
#     is_default = models.BooleanField(default=False)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.user} - {self.payment_method_type.name}"

#     def set_as_default(self):
#         UserPaymentMethod.objects.filter(user=self.user).update(is_default=False)
#         self.is_default = True
#         self.save()

#     class Meta:
#         unique_together = ['user', 'payment_method_type', 'account_name']


# class EscrowType(models.TextChoices):
#         ADVERTISER_LOCK = 'advertiser_lock', 'Advertiser Lock'
#         CREATOR_HOLD = 'creator_hold', 'Creator Hold'

# class EscrowStatus(models.TextChoices):
#     PENDING = 'pending', 'Pending'
#     RELEASED = 'released', 'Released'
#     CANCELLED = 'cancelled', 'Cancelled'
        
        
# class Escrow(models.Model):
           
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))  # For Client Lock

#     escrow_type = models.CharField(max_length=20, choices=EscrowType.choices)
#     status = models.CharField(max_length=20, choices=EscrowStatus.choices, default=EscrowStatus.PENDING)

#     release_at = models.DateTimeField(null=True, blank=True)  # Only for CREATOR_HOLD

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def release(self):
#         if self.status != EscrowStatus.PENDING:
#             return False

#         if self.escrow_type == EscrowType.ADVERTISER_LOCK:
#             self.remaining_amount = Decimal('0.00')

#         elif self.escrow_type == EscrowType.CREATOR_HOLD:
#             # move funds to Balance model
#             from payments.models import Balance, Transaction  # local import to avoid circular
#             balance = Balance.objects.get(user=self.user)
#             balance.deposit(self.amount)

#             Transaction.objects.create(
#                 user=self.user,
#                 transaction_type='deposit',
#                 amount=self.amount,
#                 balance_after_transaction=balance.available,
#                 transaction_reference=f'RELEASE-{self.id}'
#             )

#         self.status = EscrowStatus.RELEASED
#         self.save()
#         return True
    
# class WithdrawalRequest(models.Model):
#     class RequestStatus(models.TextChoices):
#         APPROVED = 'approved', 'Approved'
#         COMPLETED = 'completed', 'Completed'
#         REJECTED = 'rejected', 'Rejected'
#         PENDING = 'pending', 'Pending'
        
#     id = models.UUIDField(
#         primary_key=True, 
#         default=uuid.uuid4, 
#         editable=False)
#     user_payment_method = models.ForeignKey(
#         UserPaymentMethod, 
#         on_delete=models.SET_NULL, 
#         null=True)
#     amount = models.DecimalField(
#         max_digits=6, 
#         decimal_places=2)
#     status = models.CharField(
#         max_length=20, 
#         choices=RequestStatus.choices, 
#         default=RequestStatus.PENDING)
#     created_at = models.DateTimeField(auto_now_add=True)
#     approved_at = models.DateTimeField(null=True, blank=True)
#     completed_at = models.DateTimeField(null=True, blank=True)

#     def __str__(self):
#         return f"Withdrawal {self.id} for {self.user_payment_method.user.username}"






# # Background Release Task (e.g. Celery or Management Command)

# # from django.utils import timezone
# # from payments.models import Escrow, EscrowType

# # def release_due_escrows():
# #     now = timezone.now()
# #     escrows = Escrow.objects.filter(
# #         escrow_type=EscrowType.PROVIDER_HOLD,
# #         release_at__lte=now,
# #         status='pending'
# #     )
# #     for escrow in escrows:
# #         escrow.release()



# # class Escrow(models.Model):
# #     class Status(models.TextChoices):
# #         CANCELLED = 'cancelled', 'Cancelled'
# #         RELEASED = 'released', 'Released'
# #         PENDING = 'pending', 'Pending'
        
# #     user = models.ForeignKey(User, on_delete=models.CASCADE)
# #     amount = models.DecimalField(max_digits=10, decimal_places=2)
# #     status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
# #     payment_method = models.ForeignKey(UserPaymentMethod, on_delete=models.SET_NULL, null=True)
# #     transaction_reference = models.CharField(max_length=100, unique=True)
# #     created_at = models.DateTimeField(auto_now_add=True)
# #     updated_at = models.DateTimeField(auto_now=True)
    
# #     def __str__(self):
# #         return f"Escrow {self.transaction_reference} for {self.user.username}"
    
# #     def release_funds_from_escrow(self):
# #         from payments.models.earnings import Earning, Transaction
# #         if self.status == self.Status.PENDING:
# #             self.status = self.Status.RELEASED
# #             self.save()
# #             earning = Earning.objects.get(user=self.user)
# #             earning.deposite(self.amount)
# #             Transaction.objects.create(
# #                 user=self.user,
# #                 transaction_type='deposit',
# #                 balance_after_transaction=earning.balance,
# #                 transaction_reference=f"TRX-{self.id}-release"
# #             )

