from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid
from core.models import AdPlacement


User = get_user_model()

class AdPerformance(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    ad_placement = models.ForeignKey(
        AdPlacement, 
        on_delete=models.CASCADE, 
        related_name='performance'
    )
    date = models.DateField(auto_now_add=True)
    
    # System-side delivery metrics
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    reposts = models.PositiveIntegerField(default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Engagement (Telegram-sourced)
    total_reactions = models.IntegerField(default=0)
    total_replies = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    forwards = models.IntegerField(default=0)
    
    timestamp = models.DateTimeField(auto_now=True)
    time_delta = models.DurationField(null=True, blank=True)
    is_deducted = models.BooleanField(default=False, 
                                      help_text=_("Indicates if the cost has been \
                                          deducted from the advertiser's wallet"
                                          )
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        unique_together = ['ad_placement', 'timestamp']
        
    def __str__(self):
        return f"Performance {self.ad_placement.ad.headline} on {self.date}"
    
    
    @property
    def ctr(self):
        """Click-through rate, rounded to 2 decimal places."""
        value = (self.clicks / self.impressions * 100) if self.impressions else 0.0
        return round(value, 2)

    @property
    def cpc(self):
        """Cost per click, rounded to 2 decimal places."""
        value = (self.cost / self.clicks) if self.clicks else 0.0
        return round(value, 2)

    @property
    def conversion_rate(self):
        """Conversion rate, rounded to 2 decimal places."""
        value = (self.conversions / self.clicks * 100) if self.clicks else 0.0
        return round(value, 2)

    @property
    def engagement_rate(self):
        """Engagement rate, rounded to 2 decimal places."""
        total = self.total_reactions + self.total_replies
        value = (total / self.impressions * 100) if self.impressions else 0.0
        return round(value, 2)

    @property
    def soft_clicks(self):
        return self.clicks or self.total_reactions

    @property
    def soft_ctr(self):
        """Soft click-through rate, rounded to 2 decimal places."""
        impressions = self.impressions or 1
        value = (self.soft_clicks / impressions) * 100
        return round(value, 2)

    @property
    def viewability_rate(self):
        """Viewability rate, rounded to 2 decimal places."""
        value = (self.views / self.impressions * 100) if self.impressions else 0.0
        return round(value, 2)

    @property
    def virality_rate(self):
        """Virality rate, rounded to 2 decimal places."""
        value = (self.forwards / self.views * 100) if self.views else 0.0
        return round(value, 2)
    
    @property
    def creator_share(self):
        """Calculates the creator's share of the ad cost, rounded to 2 decimal places."""
        platform_fee = getattr(settings, 'PLATFORM_FEE', 0.15)
        value = self.cost * (1 - platform_fee)
        return round(value, 2)
