from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Value, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin.models import LogEntry
from core.models import Campaign, AdPerformance, Category
from api.serializers.campaigns import CampaignSerializer, PerformanceSerializer
from api.permissions.campaigns import IsAdvertiser
from api.serializers.advertisers import LogEntrySerializer

import logging

# Configure logging
logger = logging.getLogger(__name__)

class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]

    def get_period_dates(self, period):
        now = timezone.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'week':
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == 'month':
            start_date = now - timedelta(days=30)
            end_date = now
        elif period == 'yesterday':
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == 'last7':
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == 'last30':
            start_date = now - timedelta(days=30)
            end_date = now
        elif period == 'thisMonth':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'lastMonth':
            start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = (now.replace(day=1) - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        else:  # custom or default
            start_date = now - timedelta(days=7)
            end_date = now
        return start_date, end_date

    def get_previous_period_dates(self, period, start_date, end_date):
        delta = end_date - start_date
        return start_date - delta, end_date - delta

    def get_performance_metrics(self, start_date, end_date):
        qs = AdPerformance.objects.filter(
            ad_placement__ad__campaign__advertiser=self.request.user,
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(
            total_impressions=Coalesce(Sum('impressions'), 0),
            total_clicks=Coalesce(Sum('clicks'), 0),
            total_cost=Coalesce(Sum('cost'), Value(0.0)),
            ctr=ExpressionWrapper(
                Coalesce(Sum('clicks') * Value(1.0) / Sum('impressions'), Value(0.0)) * 100,
                output_field=FloatField()
            )
        )
        return {
            'total_spend': round(float(qs['total_cost']), 2),
            'impressions': qs['total_impressions'],
            'clicks': qs['total_clicks'],
            'ctr': round(qs['ctr'], 2)
        }

    def get_change_metrics(self, current, previous):
        def calculate_change(current_val, prev_val):
            if prev_val == 0:
                return {'class': 'text-success' if current_val > 0 else 'text-muted', 'arrow': '↑' if current_val > 0 else '', 'text': f'{current_val}'}
            change = ((current_val - prev_val) / prev_val * 100) if prev_val else 0
            return {
                'class': 'text-success' if change > 0 else 'text-danger' if change < 0 else 'text-muted',
                'arrow': '↑' if change > 0 else '↓' if change < 0 else '',
                'text': f'{abs(round(change, 1))}%'
            }

        return {
            'spend_change': calculate_change(current['total_spend'], previous['total_spend']),
            'impressions_change': calculate_change(current['impressions'], previous['impressions']),
            'clicks_change': calculate_change(current['clicks'], previous['clicks']),
            'ctr_change': calculate_change(current['ctr'], previous['ctr'])
        }

    def get_chart_data(self, start_date, end_date):
        qs = AdPerformance.objects.filter(
            ad_placement__ad__campaign__advertiser=self.request.user,
            date__gte=start_date,
            date__lte=end_date
        ).values('date').annotate(
            impressions=Coalesce(Sum('impressions'), 0),
            clicks=Coalesce(Sum('clicks'), 0),
            cost=Coalesce(Sum('cost'), Value(0.0)),
            ctr=ExpressionWrapper(
                Coalesce(Sum('clicks') * Value(1.0) / Sum('impressions'), Value(0.0)) * 100,
                output_field=FloatField()
            )
        ).order_by('date')

        labels = [str(item['date']) for item in qs]
        return {
            'labels': labels,
            'impressions': [item['impressions'] for item in qs],
            'clicks': [item['clicks'] for item in qs],
            'spend': [round(float(item['cost']), 2) for item in qs],
            'ctr': [round(item['ctr'], 2) for item in qs]
        }

    def get(self, request):
        period = request.query_params.get('period', 'last7')
        start_date, end_date = self.get_period_dates(period)
        prev_start_date, prev_end_date = self.get_previous_period_dates(period, start_date, end_date)

        # Metrics
        current_metrics = self.get_performance_metrics(start_date, end_date)
        previous_metrics = self.get_performance_metrics(prev_start_date, prev_end_date)
        change_metrics = self.get_change_metrics(current_metrics, previous_metrics)

        # Campaigns
        campaigns = Campaign.objects.filter(
            advertiser=request.user,
            is_active=True,
            status__in=['active', 'in_review', 'scheduled']
        ).select_related('advertiser').prefetch_related('ads')
        campaign_serializer = CampaignSerializer(campaigns, many=True)

        # Categories
        categories = AdPerformance.objects.filter(
            ad_placement__ad__campaign__advertiser=request.user,
            date__gte=start_date,
            date__lte=end_date
        ).values('ad_placement__channel__category__name').annotate(
            total_impressions=Coalesce(Sum('impressions'), 0),
            total_clicks=Coalesce(Sum('clicks'), 0),
            total_conversions=Coalesce(Sum('conversions'), 0),
            total_conversion_rate=ExpressionWrapper(
                Coalesce(Sum('conversions') * Value(1.0) / Sum('impressions'), Value(0.0)) * 100,
                output_field=FloatField()
            ),
            total_ctr=ExpressionWrapper(
                Coalesce(Sum('clicks') * Value(1.0) / Sum('impressions'), Value(0.0)) * 100,
                output_field=FloatField()
            )
        ).order_by('ad_placement__channel__category__name')
        categories_data = [
            {
                'category': item['ad_placement__channel__category__name'],
                'performance': {
                    'total_impressions': item['total_impressions'],
                    'total_ctr': round(item['total_ctr'], 2),
                    'total_conversion_rate': round(item['total_conversion_rate'], 2)
                }
            } for item in categories
        ]

        # Activity Logs (assuming ActivityLog model exists)
        activity_logs = LogEntry.objects.filter(
            user=request.user,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('-timestamp')[:10]
        activity_serializer = LogEntrySerializer(activity_logs, many=True)

        # Language Breakdown (mocked, adjust as needed)
        languages = [
            {'language': 'English', 'percentage': 48, 'color': '#4F46E5'},
            {'language': 'Amharic', 'percentage': 42, 'color': '#10B981'},
            {'language': 'Oromiffa', 'percentage': 10, 'color': '#F59E0B'}
        ]

        # Chart Data
        chart_data = self.get_chart_data(start_date, end_date)

        response_data = {
            'total_spend': current_metrics['total_spend'],
            'impressions': current_metrics['impressions'],
            'clicks': current_metrics['clicks'],
            'ctr': current_metrics['ctr'],
            **change_metrics,
            'active_campaigns': campaign_serializer.data,
            'categories': categories_data,
            'activity_logs': activity_serializer.data,
            'chart_data': chart_data,
            'languages': languages
        }

        logger.info(f"Fetched dashboard data for user {request.user.id} with period {period}")
        return Response(response_data, status=status.HTTP_200_OK)





class ActivityLogAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]

    def get_period_dates(self, period):
        now = timezone.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'week':
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == 'month':
            start_date = now - timedelta(days=30)
            end_date = now
        elif period == 'yesterday':
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == 'last7':
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == 'last30':
            start_date = now - timedelta(days=30)
            end_date = now
        elif period == 'thisMonth':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'lastMonth':
            start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = (now.replace(day=1) - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        else:  # custom or default
            start_date = now - timedelta(days=7)
            end_date = now
        return start_date, end_date

    def get(self, request):
        period = request.query_params.get('period', 'last7')
        start_date, end_date = self.get_period_dates(period)
        logs = LogEntry.objects.filter(
            user=request.user,
            action_time__gte=start_date,
            action_time__lte=end_date
        ).select_related('content_type').order_by('-action_time')[:10]
        serializer = LogEntrySerializer(logs, many=True)
        logger.info(f"Fetched activity logs for user {request.user.id} with period {period}")
        return Response(serializer.data, status=status.HTTP_200_OK)