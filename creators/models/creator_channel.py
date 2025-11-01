import uuid
import pytz
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from core.models import Language, Category


ALLOWED_TIMEZONES = [
    'Africa/Addis_Ababa',
    'Africa/Nairobi',
    'America/New_York',
    'Europe/London',
    'Asia/Tokyo',
    'Australia/Sydney',
    'UTC',
]


    


User = get_user_model()



class CreatorChannel(models.Model):
    
    TIMEZONE_CHOICES = [(tz, tz) for tz in ALLOWED_TIMEZONES]


    class Country(models.TextChoices):
        ET = 'ET', 'Ethiopia'
        KE = 'KE', 'Kenya'
        SA = 'SA', 'Saudi Arabia'
        AE = 'AE', 'UAE'
        RU = 'RU', 'Russia'


    class ChannelStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_REVIEW = 'in_review', 'Under Review'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'
        DELETED = 'deleted', 'Deleted'


    class PreferenceChoice(models.TextChoices):
        NONE = 'none', 'None'
        DAY = 'day', 'Daily'
        WEEK = 'week', 'Weekly'
        HOUR = 'hour', 'Hourly'
    
    
    
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'creator'},
        related_name='channels'
    )

    channel_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    channel_link = models.CharField(
        max_length=200,
        unique=True,
        help_text=_('A channel with this link already exists.')
    )

    title = models.CharField(
        max_length=255,
        default='N/A'
    )

    pp_url = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    subscribers = models.PositiveBigIntegerField(default=0)

    language = models.ManyToManyField(
        Language,
        related_name='channels',
        help_text=_('Select all that apply to your channel.')
    )

    region = models.CharField(
        max_length=3,
        choices=Country.choices,
        default=Country.ET
    )

    timezone = models.CharField(
        max_length=50,
        choices=TIMEZONE_CHOICES,
        default='Africa/Addis_Ababa',
        blank=True,
        null=True
    )

    category = models.ManyToManyField(
        Category,
        related_name='channels',
        limit_choices_to={'is_active': True}
    )

    min_cpm = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    repost_preference = models.CharField(
        max_length=20,
        choices=PreferenceChoice.choices,
        default=PreferenceChoice.DAY
    )

    repost_preference_frequency = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1)]
    )

    auto_publish = models.BooleanField(default=True)

    ml_score = models.FloatField(default=0)
    last_score_updated = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(
        max_length=50,
        choices=ChannelStatus.choices,
        default=ChannelStatus.PENDING
    )

    is_active = models.BooleanField(default=False)

    activation_code = models.CharField(
        max_length=255,
        unique=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.title

    
    def clean(self):
        super().clean()

        # Enforce no more than 3 categories
        if self.pk and self.category.count() > 3:
            raise ValidationError("You can only select up to 3 categories.")

        # Enforce a maximum of 3 active channels per user
        if not self.pk:  # Only check on creation
            existing_count = CreatorChannel.objects.filter(owner=self.owner).count()
            if existing_count >= 3:
                raise ValidationError("You can only register up to 3 channels.")

    def is_activation_expired(self):
        expiry_duration = timedelta(hours=24)
        return timezone.now() > self.created_at + expiry_duration
    
    
    
    