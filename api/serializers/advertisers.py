from rest_framework import serializers
from core.models import Campaign, Ad, AdPerformance
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType


from django.db.models import Sum, Value, FloatField, DecimalField, ExpressionWrapper, F
from django.db.models.functions import Coalesce, Cast
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# class CampaignSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Campaign
#         fields = ['id', 'name', 'status', 'start_date', 'end_date', 'budget', 'targeting_categories', 'targeting_regions']

class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ad
        fields = ['id', 'headline', 'text_content', 'img_url', 'link_url', 'is_active']


class LogEntrySerializer(serializers.ModelSerializer):
    action_flag_display = serializers.SerializerMethodField()
    content_type_name = serializers.SerializerMethodField()

    class Meta:
        model = LogEntry
        fields = ['action_time', 'user', 'content_type_name', 'object_id', 'object_repr', 'action_flag', 'action_flag_display', 'change_message']

    def get_action_flag_display(self, obj):
        action_flags = {
            ADDITION: 'Addition',
            CHANGE: 'Change',
            DELETION: 'Deletion'
        }
        return action_flags.get(obj.action_flag, 'Unknown')

    def get_content_type_name(self, obj):
        return obj.content_type.model if obj.content_type else 'Unknown'
    

class PerformanceSerializer(serializers.Serializer):
    date = serializers.DateField()
    cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    impressions = serializers.IntegerField()
    clicks = serializers.IntegerField()
    conversions = serializers.IntegerField()
    reposts = serializers.IntegerField()
    total_reactions = serializers.IntegerField()
    total_replies = serializers.IntegerField()
    views = serializers.IntegerField()
    forwards = serializers.IntegerField()
    ctr = serializers.FloatField()
    cpc = serializers.FloatField()
    cpm = serializers.FloatField()
    conversion_rate = serializers.FloatField()
    engagement_rate = serializers.FloatField()
    soft_ctr = serializers.FloatField()
    viewability_rate = serializers.FloatField()
    virality_rate = serializers.FloatField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        impressions = data['impressions'] or 0
        clicks = data['clicks'] or 0
        conversions = data['conversions'] or 0
        reposts = data['reposts'] or 0
        reactions = data['total_reactions'] or 0
        replies = data['total_replies'] or 0
        views = data['views'] or 0
        forwards = data['forwards'] or 0
        cost = data['cost'] or 0
        data['ctr'] = round((clicks / impressions * 100) if impressions else 0.0, 2)
        data['cpc'] = round((cost / clicks) if clicks else 0.0, 2)
        data['cpm'] = round((cost / impressions * 1000) if impressions else 0.0, 2)
        data['conversion_rate'] = round((conversions / clicks * 100) if clicks else 0.0, 2)
        data['engagement_rate'] = round(((reactions + replies) / impressions * 100) if impressions else 0.0, 2)
        data['soft_ctr'] = round(((clicks + reactions + replies) / impressions * 100) if impressions else 0.0, 2)
        data['viewability_rate'] = round((views / impressions * 100) if impressions else 0.0, 2)
        data['virality_rate'] = round((forwards / views * 100) if views else 0.0, 2)
        return data

class CampaignSerializer(serializers.ModelSerializer):
    performance = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Campaign
        fields = ['id', 'name', 'status', 'status_display', 'start_date', 'initial_budget', 'performance']

    def get_performance(self, obj):
        start_date = self.context['request'].query_params.get('start_date')
        end_date = self.context['request'].query_params.get('end_date')
        today = timezone.now().date() + timedelta(days=1)
        if not start_date:
            start_date = today - timedelta(days=30)
        else:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        if not end_date:
            end_date = today
        else:
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date() + timedelta(days=1)

        data = AdPerformance.objects.filter(
            ad_placement__ad__campaign=obj,
            date__gte=start_date,
            date__lt=end_date
        ).aggregate(
            total_cost=Coalesce(Sum('cost'), Value(Decimal('0.00'))),
            total_impressions=Coalesce(Sum('impressions'), Value(0)),
            total_clicks=Coalesce(Sum('clicks'), Value(0)),
            total_conversions=Coalesce(Sum('conversions'), Value(0)),
            total_reposts=Coalesce(Sum('reposts'), Value(0)),
            total_reactions=Coalesce(Sum('total_reactions'), Value(0)),
            total_replies=Coalesce(Sum('total_replies'), Value(0)),
            total_views=Coalesce(Sum('views'), Value(0)),
            total_forwards=Coalesce(Sum('forwards'), Value(0)),
        )
        impressions = data['total_impressions'] or 0
        clicks = data['total_clicks'] or 0
        conversions = data['total_conversions'] or 0
        reposts = data['total_reposts'] or 0
        reactions = data['total_reactions'] or 0
        replies = data['total_replies'] or 0
        views = data['total_views'] or 0
        forwards = data['total_forwards'] or 0
        cost = data['total_cost'] or 0
        return {
            'total_cost': float(cost),
            'total_impressions': impressions,
            'total_clicks': clicks,
            'total_conversions': conversions,
            'total_reposts': reposts,
            'total_reactions': reactions,
            'total_replies': replies,
            'total_views': views,
            'total_forwards': forwards,
            'ctr': round((clicks / impressions * 100) if impressions else 0.0, 2),
            'cpc': round((cost / clicks) if clicks else 0.0, 2),
            'cpm': round((cost / impressions * 1000) if impressions else 0.0, 2),
            'conversion_rate': round((conversions / clicks * 100) if clicks else 0.0, 2),
            'engagement_rate': round(((reactions + replies) / impressions * 100) if impressions else 0.0, 2),
            'soft_ctr': round(((clicks + reactions + replies) / impressions * 100) if impressions else 0.0, 2),
            'viewability_rate': round((views / impressions * 100) if impressions else 0.0, 2),
            'virality_rate': round((forwards / views * 100) if views else 0.0, 2),
        }

