import uuid
from django.utils import timezone

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.contrib.auth import get_user_model

from core.models import Category, Language, ActiveManager
from core.utils.helper import is_valid_url


User = get_user_model()


class AdStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    IN_REVIEW = 'in_review', 'In Review'
    SCHEDULED = 'scheduled', 'Scheduled'
    ACTIVE = 'active', 'Active'
    ON_HOLD = 'on_hold', 'On Hold'
    STOPPED = 'stopped', 'Stopped'
    DECLINED = 'declined', 'Declined'
    COMPLETED = 'completed', 'Completed'

class AdObjective(models.TextChoices):
    BRAND_AWARENESS = 'brand_awareness', 'Brand Awareness'
    ENGAGEMENT = 'engagement', 'Engagement'
    CONVERSION = 'conversion', 'Conversion'
    TRAFFIC = 'traffic', 'Traffic'

    

class Campaign(models.Model):
    
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    advertiser = models.ForeignKey(
        User,
        on_delete=models.CASCADE, 
        limit_choices_to={'user_type': 'advertiser'}, 
        related_name='campaigns'
    )
    name = models.CharField(max_length=255)
    objective = models.CharField(
        max_length=20, 
        choices=AdObjective.choices, 
        default=AdObjective.BRAND_AWARENESS
    )
    initial_budget = models.DecimalField(
        max_digits=12, 
        decimal_places=2
    )
    total_spent = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0
    )
    cpm = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    views_frequency_cap = models.IntegerField(default=1)
    
    targeting_languages = models.ManyToManyField(
        Language,
        help_text=_('Select all languages that you are targeting'),
        related_name='campaigns',
    )
    targeting_regions = models.JSONField(default=dict)
    targeting_categories = models.ManyToManyField(Category, related_name='campaigns')
    
    status = models.CharField(max_length=20, choices=AdStatus, default=AdStatus.STOPPED)
    admin_notes = models.TextField(null=True, blank=True, default='')
    is_active = models.BooleanField(default=True)

    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ('-updated_at',)
        unique_together = ['name', 'advertiser', 'status']
        
        permissions = [
            ('pause_campaign', 'Can pause campaigns'),
            ('start_campaign', 'Can start campaigns'),
            ('activate_campaign', 'Can activate reviewed campaigns'),
            ('decline_campaign', 'Can decline reviewed campaigns'),
            ('resubmit_campaign', 'Can resubmit declined campaigns'),
            ('remoderate_campaign', 'Can initiat remoderation active campaign campaigns'),
            ('restart_campaign', 'Can restart stopped campaigns'),
        ]
    
    def __str__(self):
        return self.name
    
    objects = models.Manager()  # Default manager
    active = ActiveManager()  # Custom manager for active campaigns
    

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date.")

    def update_status_based_on_budget(self):
        if self.initial_budget <= 0 or (self.end_date and self.end_date < timezone.now().date()):
            self.status = AdStatus.COMPLETED
            self.save()
      
      
class Ad(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='ads')
    headline = models.CharField(max_length=255)
    text_content = models.TextField()
    img_url = models.CharField(max_length=255, null=True, blank=True)
    brand_name = models.CharField(max_length=50, null=True, blank=True)
    social_links = models.JSONField(
        default=list,
        blank=True,
        help_text=_('A list of up to 3 social media links, e.g., \
            [{"platform": "X", "url": "https://x.com/username"}, \
                {"platform": "Website", "url": "https://example.com"}]')
    )
    
    ml_score = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.headline
    
    def clean(self):
        if not isinstance(self.social_links, list):
            raise ValidationError({'social_links': 'Social links must be a list.'})
        if len(self.social_links) > 3:
            raise ValidationError({'social_links': 'Maximum of 3 social links allowed.'})
        for link in self.social_links:
            if not isinstance(link, dict) or 'platform' not in link or 'url' not in link:
                raise ValidationError({'social_links': 'Each social link must have a platform and URL.'})
            if not is_valid_url(link['url']):
                raise ValidationError({'social_links': f"Invalid URL: {link['url']}"})
     


 