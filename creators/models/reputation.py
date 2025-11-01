import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from creators.models import CreatorChannel


User = get_user_model()


class CreatorReputation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )    
    creator_channel = models.OneToOneField(
        CreatorChannel,
        on_delete=models.CASCADE,
        related_name='reputation'
    )

    rating = models.FloatField(default=5.0)
    fraud_score = models.FloatField(default=0.0)
    total_complaints = models.IntegerField(default=0)
    last_reviewed = models.DateTimeField(null=True, blank=True)
    avg_engagement_rate = models.FloatField(
        default=0.0,
        verbose_name="Soft Engagement Rate (%)"
    )

    estimated_views_avg = models.IntegerField(
        default=0,
        verbose_name="Estimated Views (Average)"
    )
    estimated_views_max = models.IntegerField(
        default=0,
        verbose_name="Estimated Views (Top Post)"
    )
    
    estimated_cost_min = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Estimated Campaign Cost (Min)"
    )
    estimated_cost_max = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Estimated Campaign Cost (Max)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.creator_channel.owner} - {self.rating:.2f}"
    
    
    class Meta:
        verbose_name = "Creator Reputation"
        verbose_name_plural = "Creator Reputations"
        ordering = ['-updated_at']