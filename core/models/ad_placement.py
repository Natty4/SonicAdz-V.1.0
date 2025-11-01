from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid
from creators.models import CreatorChannel
from core.models import Campaign, Ad


User = get_user_model()
   
class AdPlacementStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    RUNNING = 'running', 'Live'
    REJECTED = 'rejected', 'Rejected'
    PAUSED = 'paused', 'Paused'
    STOPPED = 'stopped', 'Stopped'
    COMPLETED = 'completed', 'Completed'
    EXPIRED = 'expired', 'Expired'

class AdPlacement(models.Model):

    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False)
    ad = models.ForeignKey(
        Ad, 
        on_delete=models.CASCADE, 
        related_name='placements', 
        limit_choices_to={
            'is_active':True, 
            'campaign__status__in': ['on_hold', 'active']
            }
    )
    channel = models.ForeignKey(
        CreatorChannel, 
        on_delete=models.CASCADE, 
        related_name='ad_placements',
        limit_choices_to={
            'is_active':True, 
            'status': 'verified'
            }
    )
    placed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50, 
        choices=AdPlacementStatus.choices,
        default=AdPlacementStatus.PENDING
    )

    winning_bid_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )
    repost_count = models.IntegerField(default=0)
    max_reposts = models.IntegerField(default=3)
    preference_score = models.FloatField(default=1.0)
    
    content_platform_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # active = ActiveManager()
    objects = models.Manager()  
    
    class CampaignManager(models.Manager):
        def active(self):
            return self.filter(is_active=True)
        
    objects = CampaignManager() 
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status  

    class Meta:
        unique_together = ['ad', 'channel']
        
    def __str__(self):
        return f"AdPlacement: {self.ad.headline} → {self.channel.title}"
    
    
# Placement Match Log
class PlacementMatchLog(models.Model):
    campaign = models.ForeignKey(
        Campaign, 
        on_delete=models.CASCADE, 
        related_name='ad_placements_match_log'
    )
    ad_placement = models.ForeignKey(
        AdPlacement, 
        on_delete=models.CASCADE
    )
    matched_on = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()  # explanation of why match occurred
    
    # New field to store estimated cost at time of matching
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_("Estimated cost at the time of match")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ad_placement.channel.title} - {self.ad_placement.ad.headline}"
  