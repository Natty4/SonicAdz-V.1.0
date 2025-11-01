from django.shortcuts import render
from django.utils.timezone import now
from django.contrib.admin.models import LogEntry
from django.db.models import Sum, Value, FloatField
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import permission_classes
from datetime import timedelta
import json
from django.core.serializers.json import DjangoJSONEncoder
from decimal import Decimal
from core.models import AdPerformance, AdPlacement, Campaign, AdStatus
from api.permissions.campaigns import IsAdvertiser


@login_required
@permission_classes([IsAdvertiser])
def advertiser_dashboard(request):
    advertiser = request.user
    today = now().date() + timedelta(days=1)
    period = request.GET.get('period', 'last30')
    
    # --- Period Handling ---
    if period == 'today':
        current_start = today - timedelta(days=1)
        previous_start = today - timedelta(days=2)
        previous_end = today - timedelta(days=1)
    elif period == 'week':
        current_start = today - timedelta(days=7)
        previous_start = today - timedelta(days=14)
        previous_end = today - timedelta(days=7)
    elif period == 'month':
        current_start = today - timedelta(days=30)
        previous_start = today - timedelta(days=60)
        previous_end = today - timedelta(days=30)
    else:  # last30 or custom
        current_start = today - timedelta(days=30)
        previous_start = today - timedelta(days=60)
        previous_end = today - timedelta(days=30)
    
    # Custom date range from GET params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        from datetime import datetime
        try:
            current_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date() + timedelta(days=1)
            delta = end_date - current_start
            previous_start = current_start - delta
            previous_end = current_start
        except ValueError:
            pass

    # --- Helper Functions ---

    def safe(val):
        return val or 0

    def format_change(current, previous):
        try:
            current = float(safe(current))
            previous = float(safe(previous))
        except (TypeError, ValueError):
            return "0%", "neutral", ""
        if previous == 0:
            if current == 0:
                return "0%", "neutral", ""
            return "+∞%", "positive", "↑"
        try:
            change = ((current - previous) / previous) * 100
            return f"{change:+.1f}%", "positive" if change >= 0 else "negative", "↑" if change >= 0 else "↓"
        except ZeroDivisionError:
            return "0%", "neutral", ""

    def get_totals(queryset, date_range):
        start, end = date_range
        data = queryset.filter(date__gte=start, date__lt=end).aggregate(
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
        impressions = safe(data['total_impressions'])
        clicks = safe(data['total_clicks'])
        conversions = safe(data['total_conversions'])
        reposts = safe(data['total_reposts'])
        reactions = safe(data['total_reactions'])
        replies = safe(data['total_replies'])
        views = safe(data['total_views'])
        forwards = safe(data['total_forwards'])
        cost = safe(data['total_cost'])
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
            'ctr': round((clicks / impressions * 100) if impressions else 0, 2),
            'cpc': round((cost / clicks) if clicks else 0, 2),
            'cpm': round((cost / impressions * 1000) if impressions else 0, 2),
            'conversion_rate': round((conversions / clicks * 100) if clicks else 0, 2),
            'engagement_rate': round(((reactions + replies) / impressions * 100) if impressions else 0, 2),
            'soft_ctr': round(((clicks + reactions + replies) / impressions * 100) if impressions else 0, 2),
            'viewability_rate': round((views / impressions * 100) if impressions else 0, 2),
            'virality_rate': round((forwards / views * 100) if views else 0, 2),
        }

    def get_category_performance(model, placements, date_range):
        start, end = date_range
        queryset = model.objects.filter(
            ad_placement__in=placements,
            date__gte=start,
            date__lt=end
        ).values('ad_placement__channel__category__name').annotate(
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
        result = {}
        for row in queryset:
            category = row['ad_placement__channel__category__name'] or "Uncategorized"
            impressions = safe(row['total_impressions'])
            clicks = safe(row['total_clicks'])
            conversions = safe(row['total_conversions'])
            reposts = safe(row['total_reposts'])
            reactions = safe(row['total_reactions'])
            replies = safe(row['total_replies'])
            views = safe(row['total_views'])
            forwards = safe(row['total_forwards'])
            cost = safe(row['total_cost'])
            result[category] = {
                'total_cost': float(cost),
                'total_impressions': impressions,
                'total_clicks': clicks,
                'total_conversions': conversions,
                'total_reposts': reposts,
                'total_reactions': reactions,
                'total_replies': replies,
                'total_views': views,
                'total_forwards': forwards,
                'ctr': round((clicks / impressions * 100) if impressions else 0, 2),
                'cpc': round((cost / clicks) if clicks else 0, 2),
                'cpm': round((cost / impressions * 1000) if impressions else 0, 2),
                'conversion_rate': round((conversions / clicks * 100) if clicks else 0, 2),
                'engagement_rate': round(((reactions + replies) / impressions * 100) if impressions else 0, 2),
                'soft_ctr': round(((clicks + reactions + replies) / impressions * 100) if impressions else 0, 2),
                'viewability_rate': round((views / impressions * 100) if impressions else 0, 2),
                'virality_rate': round((forwards / views * 100) if views else 0, 2),
            }
        return result

    # --- Data Fetching ---
    # Calculate total number of active campaigns
    active_campaign_count = Campaign.objects.filter(
        advertiser=request.user, 
        status=AdStatus.ACTIVE
    ).count()
    placements = AdPlacement.objects.filter(ad__campaign__advertiser=advertiser)
    
    # Totals
    current_totals = get_totals(AdPerformance.objects.filter(ad_placement__in=placements), (current_start, today))
    previous_totals = get_totals(AdPerformance.objects.filter(ad_placement__in=placements), (previous_start, previous_end))

    # Changes
    spend_change = format_change(current_totals['total_cost'], previous_totals['total_cost'])
    impressions_change = format_change(current_totals['total_impressions'], previous_totals['total_impressions'])
    clicks_change = format_change(current_totals['total_clicks'], previous_totals['total_clicks'])
    ctr_change = format_change(current_totals['ctr'], previous_totals['ctr'])
    conversion_rate_change = format_change(current_totals['conversion_rate'], previous_totals['conversion_rate'])
    engagement_rate_change = format_change(current_totals['engagement_rate'], previous_totals['engagement_rate'])
    soft_ctr_change = format_change(current_totals['soft_ctr'], previous_totals['soft_ctr'])
    viewability_rate_change = format_change(current_totals['viewability_rate'], previous_totals['viewability_rate'])
    virality_rate_change = format_change(current_totals['virality_rate'], previous_totals['virality_rate'])

    # Category Performance
    categorical_performance = get_category_performance(AdPerformance, placements, (current_start, today))

    # Activity Logs
    activity_logs = LogEntry.objects.filter(user=advertiser).order_by('-action_time')[:6]

    # Mocked Language Breakdown
    languages = [
        {'language': 'English', 'percentage': 48, 'color': '#4F46E5'},
        {'language': 'Amharic', 'percentage': 42, 'color': '#10B981'},
        {'language': 'Oromiffa', 'percentage': 10, 'color': '#F59E0B'}
    ]

    # Metrics and Labels for Template
    metric_labels = [
        ('total_cost', 'Total Spend'),
        ('total_impressions', 'Impressions'),
        ('total_clicks', 'Clicks'),
        ('ctr', 'CTR'),
        ('total_conversions', 'Conversions'),
        ('conversion_rate', 'Conversion Rate'),
        ('total_reactions', 'Reactions'),
        ('total_replies', 'Replies'),
        ('total_views', 'Views'),
        ('total_forwards', 'Forwards'),
        ('engagement_rate', 'Engagement Rate'),
        ('soft_ctr', 'Soft CTR'),
        ('viewability_rate', 'Viewability Rate'),
        ('virality_rate', 'Virality Rate'),
        ('cpc', 'CPC'),
        ('cpm', 'CPM'),
    ]

    # --- Context ---
    context = {
        'advertiser': advertiser,
        'summary': {
            'total_active_ads': active_campaign_count,
            'total_cost': current_totals['total_cost'],
            'total_impressions': current_totals['total_impressions'],
            'total_clicks': current_totals['total_clicks'],
            'total_conversions': current_totals['total_conversions'],
            'total_reposts': current_totals['total_reposts'],
            'total_reactions': current_totals['total_reactions'],
            'total_replies': current_totals['total_replies'],
            'total_views': current_totals['total_views'],
            'total_forwards': current_totals['total_forwards'],
            'ctr': current_totals['ctr'],
            'cpc': current_totals['cpc'],
            'cpm': current_totals['cpm'],
            'conversion_rate': current_totals['conversion_rate'],
            'engagement_rate': current_totals['engagement_rate'],
            'soft_ctr': current_totals['soft_ctr'],
            'viewability_rate': current_totals['viewability_rate'],
            'virality_rate': current_totals['virality_rate'],
        },
        'spend_change': {'text': spend_change[0], 'class': spend_change[1], 'arrow': spend_change[2]},
        'impressions_change': {'text': impressions_change[0], 'class': impressions_change[1], 'arrow': impressions_change[2]},
        'clicks_change': {'text': clicks_change[0], 'class': clicks_change[1], 'arrow': clicks_change[2]},
        'ctr_change': {'text': ctr_change[0], 'class': ctr_change[1], 'arrow': ctr_change[2]},
        'conversion_rate_change': {'text': conversion_rate_change[0], 'class': conversion_rate_change[1], 'arrow': conversion_rate_change[2]},
        'engagement_rate_change': {'text': engagement_rate_change[0], 'class': engagement_rate_change[1], 'arrow': engagement_rate_change[2]},
        'soft_ctr_change': {'text': soft_ctr_change[0], 'class': soft_ctr_change[1], 'arrow': soft_ctr_change[2]},
        'viewability_rate_change': {'text': viewability_rate_change[0], 'class': viewability_rate_change[1], 'arrow': viewability_rate_change[2]},
        'virality_rate_change': {'text': virality_rate_change[0], 'class': virality_rate_change[1], 'arrow': virality_rate_change[2]},
        'categories': categorical_performance.items(),
        'activity_logs': activity_logs,
        'languages': languages,
        'period': period,
        'start_date': start_date or current_start.strftime('%Y-%m-%d'),
        'end_date': (end_date - timedelta(days=1)).strftime('%Y-%m-%d') if end_date else (today - timedelta(days=1)).strftime('%Y-%m-%d'),
       
    }

    metrics = []
    metric_definitions = [
        ('total_cost', 'Total Spend'),
        ('total_impressions', 'Impressions'),
        ('total_clicks', 'Clicks'),
        ('ctr', 'CTR'),
        ('total_conversions', 'Conversions'),
        ('conversion_rate', 'Conversion Rate'),
        ('total_reactions', 'Reactions'),
        ('total_replies', 'Replies'),
        ('total_views', 'Views'),
        ('total_forwards', 'Forwards'),
        ('engagement_rate', 'Engagement Rate'),
        ('soft_ctr', 'Soft CTR'),
        ('viewability_rate', 'Viewability Rate'),
        ('virality_rate', 'Virality Rate'),
        ('cpc', 'CPC'),
        ('cpm', 'CPM'),
    ]

    for metric, label in metric_definitions:
        change = context.get(f"{metric}_change", {'text': '0%', 'class': 'neutral', 'arrow': ''})
        metrics.append({
            'metric': metric,
            'label': label,
            'value': current_totals.get(metric, 0),
            'change_text': change['text'],
            'change_class': change['class'],
            'change_arrow': change['arrow'],
        })

    # Now add the metrics to context
    context['metrics'] = metrics
    return render(request, 'advertiser/dashboard.html', context)