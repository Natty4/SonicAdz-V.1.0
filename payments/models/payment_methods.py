import uuid
from django.db import models
from django.contrib.auth import get_user_model
from phonenumber_field.modelfields import PhoneNumberField
User = get_user_model()

class PaymentMethodType(models.Model):
    class MethodCategory(models.TextChoices):
        BANK = 'bank', 'Bank'
        WALLET = 'wallet', 'Mobile Wallet'
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    name = models.CharField(
        max_length=100,
        unique=True)  # e.g. "TeleBirr", "M-Pesa"
    short_name = models.CharField(
        max_length=10,
        null=True,
        blank=True)
    category = models.CharField(
        max_length=20,
        choices=MethodCategory.choices)
    logo = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional logo (PNG, SVG, etc.)")
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

class UserPaymentMethod(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payment_methods')
    payment_method_type = models.ForeignKey(
        PaymentMethodType,
        on_delete=models.CASCADE,
        related_name='user_payment_methods')
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    phone_number = PhoneNumberField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.user} - {self.payment_method_type.name}"
    def set_as_default(self):
        if self.status != self.Status.VERIFIED:
            return False  # Not allowed to be default unless verified
        UserPaymentMethod.objects.filter(user=self.user).update(is_default=False)
        self.is_default = True
        self.save()
        return True  # Successfully updated
    def get_display_reference(self):
        if self.payment_method_type.category == self.payment_method_type.MethodCategory.BANK and self.account_number:
            return self.account_number[-4:]
        elif self.phone_number:
            return str(self.phone_number)[-4:]
        return "****"
    class Meta:
        unique_together = ['user', 'payment_method_type', 'account_name']












































# import uuid


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
#         unique=True)  # e.g. "TeleBirr", "M-Pesa"
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
#         if self.status != self.Status.VERIFIED:
#             return False  # Not allowed to be default unless verified

#         UserPaymentMethod.objects.filter(user=self.user).update(is_default=False)
#         self.is_default = True
#         self.save()
#         return True  # Successfully updated

#     def get_display_reference(self):
#         if self.payment_method_type.category == self.payment_method_type.MethodCategory.BANK and self.account_number:
#             return self.account_number[-4:]
#         elif self.phone_number:
#             return str(self.phone_number)[-4:]
#         return "****"

#     class Meta:
#         unique_together = ['user', 'payment_method_type', 'account_name']
