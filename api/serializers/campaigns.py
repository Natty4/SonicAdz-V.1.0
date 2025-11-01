from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from core.models import Campaign, Ad, Language, Category, AdPerformance, AdStatus
from core.services.matching_engine import CampaignChannelMatcher
from core.services.ad_placement_engine import AdPlacementEngine
from core.utils.helper import *
from django.db import transaction
from django.utils.translation import gettext_lazy as _

import logging

logger = logging.getLogger(__name__)


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'name', 'code']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'icon']


def _handle_media_upload(validated_data):
    """Internal helper to process media file upload."""
    media_file = validated_data.pop('media_file', None)
    if media_file:
        headline = validated_data.get('headline', '')
        public_id = get_unique_public_id(headline)
        validated_data['img_url'] = upload_to_cloudinary(media_file, public_id)
    elif 'img_url' in validated_data and validated_data['img_url'] == '':
        validated_data['img_url'] = ''

class AdSerializer(serializers.ModelSerializer):
    media_file = serializers.FileField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Ad
        fields = (
            'id', 'campaign', 'headline', 'text_content',
            'img_url', 'brand_name', 'social_links',
            'ml_score', 'is_active', 'media_file' 
        )
        read_only_fields = ('id', 'campaign', 'ml_score', 'is_active')

    def validate(self, data):
        social_links = data.get('social_links', [])
        if not isinstance(social_links, list):
            raise serializers.ValidationError({'social_links': 'Social links must be a list.'})
        if len(social_links) > 3:
            raise serializers.ValidationError({'social_links': 'Maximum of 3 social links allowed.'})
        valid_platforms = {'X', 'Instagram', 'TikTok', 'Facebook', 'YouTube', 'Website', 'Telegram', 'Linkedin', 'Other'}
        for link in social_links:
            if not isinstance(link, dict) or 'platform' not in link or 'url' not in link:
                raise serializers.ValidationError({'social_links': 'Each social link must have a platform and URL.'})
            if link['platform'] not in valid_platforms:
                raise serializers.ValidationError({'social_links': f"Invalid platform: {link['platform']}. Must be one of {valid_platforms}."})
            if not link['platform']:
                raise serializers.ValidationError({'social_links': 'Platform name cannot be empty.'})
            if 'is_valid_url' in globals() and not is_valid_url(link['url']):
                 raise serializers.ValidationError({'social_links': f"Invalid URL: {link['url']}"})

        img_url = data.get('img_url')
        media_file = data.get('media_file')
        
        if not img_url and not media_file:
            if not data.get('headline'):
                 raise serializers.ValidationError({'headline': 'Headline is required when uploading a file or providing an img_url.'})
            raise serializers.ValidationError({'img_url': 'Either an image URL or a media file must be provided.'})
            
        if img_url and media_file:
            raise serializers.ValidationError({'img_url': 'Provide either an image URL or a media file, not both.'})
            
        if img_url and 'is_valid_url' in globals() and not is_valid_url(img_url):
            raise serializers.ValidationError({'img_url': 'Invalid URL format.'})

        return data

    def create(self, validated_data):
        _handle_media_upload(validated_data) 
 
        return super().create(validated_data)

    def update(self, instance, validated_data):

        _handle_media_upload(validated_data)
        
        
        return super().update(instance, validated_data)
class CampaignSerializer(serializers.ModelSerializer):
    
    ad_content = serializers.SerializerMethodField()
    ad_content_write = AdSerializer(write_only=True, required=False) 
    
    # M2M fields 
    targeting_languages = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Language.objects.all(), required=False
    )
    targeting_categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all(), required=False
    )

    class Meta:
        model = Campaign
        fields = (
            'id', 'advertiser', 'name', 'objective', 'initial_budget', 
            'cpm', 'start_date', 'end_date', 'views_frequency_cap', 
            'targeting_languages', 'targeting_regions', 'targeting_categories', 
            'status', 'ad_content', 'ad_content_write',
            'total_spent', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'advertiser', 'status', 'total_spent', 'created_at', 'updated_at')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance is None:
            self.fields['ad_content_write'].required = True
        else:
            self.fields['ad_content_write'].required = False

    def to_internal_value(self, data):
        # Handle FormData with nested ad_content_write
        if hasattr(data, 'getlist'):
            # This is likely FormData
            ad_content_write_data = {}
            for key in data.keys():
                if key.startswith('ad_content_write['):
                    # Extract nested field name
                    field_name = key.split('[')[1].rstrip(']')
                    ad_content_write_data[field_name] = data.get(key)
            
            if ad_content_write_data:
                data = data.copy()
                data['ad_content_write'] = ad_content_write_data
        
        return super().to_internal_value(data)
    
    def validate(self, data):
        """
        Ensures the combination of (name, advertiser, status) is unique before saving.
        """
        advertiser = self.context['request'].user
        
        new_name = data.get('name', self.instance.name if self.instance else None)
        new_status = data.get('status', self.instance.status if self.instance else AdStatus.DRAFT)
        
        if not new_name:
             new_name = self.instance.name
        
        qs = Campaign.objects.filter(
            name=new_name, 
            advertiser=advertiser, 
            status=new_status
        )
        
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                {'non_field_errors': f"A campaign '{new_name}' \
                    already exists for this advertiser with the status '{new_status}'.\
                        Please rename the campaign."}
            )
            
        instance = self.instance
        new_cpm = data.get('cpm')

        if instance and new_cpm is not None:                   
            if instance.status == AdStatus.ACTIVE:             
                if new_cpm < instance.cpm:
                    raise serializers.ValidationError({
                        'cpm': (
                            f"The CPM cannot be lowered on an active campaign. "
                            f"Current CPM: {instance.cpm:.2f} ETB. "
                            f"You may increase it or keep the same value."
                        )
                    })
        return data

    def get_ad_content(self, instance):
        """Retrieves the currently active ad for serialization."""
        try:
            active_ad = instance.ads.get(is_active=True)
            return AdSerializer(active_ad).data
        except Ad.DoesNotExist:
            return None

    @transaction.atomic
    def create(self, validated_data):
        ad_content_data = validated_data.pop('ad_content_write') 
        
        targeting_languages_data = validated_data.pop('targeting_languages', [])
        targeting_categories_data = validated_data.pop('targeting_categories', [])
        
        validated_data['status'] = AdStatus.DRAFT
        campaign = Campaign.objects.create(**validated_data)

        ad_serializer = AdSerializer(data=ad_content_data)
        ad_serializer.is_valid(raise_exception=True)
        ad_serializer.save(campaign=campaign, is_active=True)
        
        campaign.targeting_languages.set(targeting_languages_data)
        campaign.targeting_categories.set(targeting_categories_data)
        
        return campaign
    
    @transaction.atomic
    def update(self, instance, validated_data):
        ad_content_data = validated_data.pop('ad_content_write', None)
        
        targeting_languages_data = validated_data.pop('targeting_languages', None)
        targeting_categories_data = validated_data.pop('targeting_categories', None)

        if ad_content_data:
            editable_statuses = [AdStatus.DRAFT, AdStatus.STOPPED]
            if instance.status not in editable_statuses:
                raise serializers.ValidationError(
                    {'ad_content': f"Ad content can only be updated when the campaign status is {AdStatus.DRAFT} or {AdStatus.STOPPED}."}
                )

            # Get or create the active ad
            active_ad, created = Ad.objects.get_or_create(
                campaign=instance,
                is_active=True,
                defaults=ad_content_data
            )
            
            if not created:
                # Update existing active ad
                ad_serializer = AdSerializer(active_ad, data=ad_content_data, partial=True)
                ad_serializer.is_valid(raise_exception=True)
                ad_serializer.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if targeting_languages_data is not None:
            instance.targeting_languages.set(targeting_languages_data)
        if targeting_categories_data is not None:
            instance.targeting_categories.set(targeting_categories_data)
            
        if instance.status not in [AdStatus.DRAFT]:
            if not instance.ads.filter(is_active=True).exists():
                raise ValidationError("Campaign must have at least one active ad before assigning placements.")

            top_matches = CampaignChannelMatcher(instance).get_ranked_channels(top_n=25)
            if top_matches:
                engine = AdPlacementEngine(instance, top_matches)
                assigned = engine.assign_placements()
        return instance
     
class PerformanceSerializer(serializers.ModelSerializer):
    ctr = serializers.ReadOnlyField()
    cpc = serializers.ReadOnlyField()
    cpm = serializers.ReadOnlyField()
    conversion_rate = serializers.ReadOnlyField()
    engagement_rate = serializers.ReadOnlyField()
    soft_ctr = serializers.ReadOnlyField()
    viewability_rate = serializers.ReadOnlyField()
    virality_rate = serializers.ReadOnlyField()

    class Meta:
        model = AdPerformance
        fields = ['id', 'date', 'impressions', 'clicks', 'conversions', 'reposts', 'cost', 
                  'total_reactions', 'total_replies', 'views', 'forwards', 'ctr', 'cpc', 'cpm', 
                  'conversion_rate', 'engagement_rate', 'soft_ctr', 'viewability_rate', 'virality_rate',
                  'created_at', 'updated_at']
        read_only_fields = fields