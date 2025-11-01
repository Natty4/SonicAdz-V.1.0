from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.core.exceptions import ValidationError
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import MinLengthValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
import uuid



# User & Roles

class UserType(models.TextChoices):
        ADVERTISER = 'advertiser', _('Advertiser')
        CREATOR = 'creator', _('Content Creator')
        MODERATOR = 'moderator', _('Moderator')
        STAFF = 'staff', _('Staff Member')
        
class User(AbstractUser, PermissionsMixin):
    
    # Authentication fields
    phone_number = PhoneNumberField(
        unique=True,
        verbose_name=_('Phone Number'),
        help_text=_('Required. International format with country code (e.g. +251...)'),
        error_messages={
            'unique': _("A user with that phone number already exists."),
        }
    )
    
    # User profile fields
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.CREATOR,
        verbose_name=_('User Type')
    )
    
    address = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('Physical Address')
    )
    
    # Security fields
    email_verified = models.BooleanField(
        default=False,
        verbose_name=_('Email Verified')
    )
    
    phone_verified = models.BooleanField(
        default=False,
        verbose_name=_('Phone Verified')
    )
    
    last_seen = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last Seen')
    )
    
    # Settings
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username', 'user_type']
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['user_type']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name() or self.username}"
    
    @property
    def is_staff_member(self):
        return self.user_type in [self.UserType.STAFF, self.UserType.MODERATOR]
    
    @property
    def display_name(self):
        return self.get_full_name() or self.username 
    
    def save(self, *args, **kwargs):
        # Ensure username is set if not provided
        if not self.username:
            self.username = f"user_{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)
 
 

class TelegramProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='telegram_profile',
        verbose_name=_('User Account')
    )
    
    tg_id = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_('Telegram User ID'),
        help_text=_('Unique identifier from Telegram'),
        validators=[MinLengthValidator(5)]
    )
    
    username = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name=_('Telegram Username'),
        help_text=_('@username if available')
    )
    
    first_name = models.CharField(
        max_length=64,
        verbose_name=_('First Name')
    )
    
    last_name = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name=_('Last Name')
    )
    
    language_code = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_('Language Code')
    )
    
    photo_url = models.URLField(
        null=True,
        blank=True,
        verbose_name=_('Profile Photo URL')
    )
    is_premium = models.BooleanField(default=False)
    
    auth_date = models.DateTimeField(
        verbose_name=_('Authentication Date')
    )
    
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last Updated')
    )
    
    class Meta:
        verbose_name = _('Telegram Profile')
        verbose_name_plural = _('Telegram Profiles')
        ordering = ['-auth_date']
    
    def __str__(self):
        return f"Telegram profile for {self.user}"
        
    def clean(self):
        if self.user.user_type != UserType.CREATOR:
            raise ValidationError("Telegram profiles can only be created for creators")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)




