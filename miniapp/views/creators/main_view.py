from django.utils import timezone
from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import json
import logging

from django.db.models import Sum, F, Prefetch, DecimalField
from datetime import timedelta

from api.serializers.creators import UserPaymentMethodSerializer
from creators.models import CreatorChannel
from payments.models import UserPaymentMethod
from payments.services import BalanceService  
from core.models import AdPlacement, AdPerformance, Notification
from miniapp.models import TelegramVisitorLog
from django.contrib.admin.models import LogEntry
from rest_framework import status, permissions
from rest_framework.decorators import permission_classes

from users.models import TelegramProfile, UserType
from django.contrib.auth import get_user_model
from .auth_view import process_telegram_auth_view
from miniapp.utils import get_device_info, get_client_ip


logger = logging.getLogger(__name__)


User = get_user_model()


def landing_view(request):
    
    if request.method == 'GET':
        try:
            ip = get_client_ip(request)
            device_info = get_device_info(request)

            TelegramVisitorLog.objects.create(
                telegram_id=None,  # not available yet
                username=None,
                first_name=None,
                last_name=None,
                is_premium=False,
                ip_address=ip,
                user_agent=device_info["user_agent_str"],
                device_type=(
                    "mobile" if device_info["is_mobile"]
                    else "tablet" if device_info["is_tablet"]
                    else "pc" if device_info["is_pc"]
                    else "bot" if device_info["is_bot"]
                    else "unknown"
                ),
                os=device_info["os"],
                browser=device_info["browser"],
                device_name=device_info["device"],
            )
            request.session["logged_landing_visit"] = True  # Prevent duplicate logging
        except Exception as e:
            logger.warning(f"Landing visitor logging failed: {e}")
            
    # If POST request, it's the form submission - let process_telegram_auth_view handle it
    if request.method == 'POST':
        return process_telegram_auth_view(request)
        
    # For GET requests, show the landing page
    # Check if user is already logged in and is a creator
    user = request.user

    if user.is_authenticated and user.user_type == UserType.CREATOR and request.session.get("auth_source") == "telegram":
        return redirect('creator:main')
    # Otherwise, render authentication view
    context = {
        'bot': settings.BOT_LINK,
    }
    return render(request, 'landing/index.html', context)

   
class IsCreatorUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == UserType.CREATOR

 
# @login_required
# def dashboard_view(request):
#     user = request.user
#     time_threshold = timezone.now() - timedelta(days=28)

#     # Top 3 Channels by Subscribers
#     top_channels = CreatorChannel.objects.filter(
#         owner=user,
#         is_active=True
#     ).order_by('-subscribers')[:3]

#     # Active Ad Placements (Running or Approved)
#     active_ad_placements = AdPlacement.objects.filter(
#         channel__owner=user,
#         status__in=['running', 'approved'],
#         is_active=True
#     ).select_related('ad', 'channel').prefetch_related(
#         Prefetch(
#             'performance',
#             queryset=AdPerformance.objects.filter(date__gte=time_threshold)
#         )
#     )[:5]


#     weekly_data = AdPerformance.objects.filter(
#         ad_placement__channel__owner=user,
#         date__gte=time_threshold
#     ).values('date__week').annotate(
#         total_impressions=Sum('impressions'),
#         total_earnings=Sum(F('cost') * 0.85, output_field=DecimalField())
#     ).order_by('date__week')

#     chart_data = [0, 0, 0, 0]
#     week_labels = []

#     for i, week_data in enumerate(weekly_data):
#         if i < 4:
#             chart_data[i] = float(week_data['total_earnings'] or 0)
#             week_number = week_data['date__week']
#             week_labels.append(f"Week {week_number}")

    
#     balance_summary = BalanceService.get_balance_summary(user, role="creator")

#     # Active payment methods
#     payment_methods = UserPaymentMethod.objects.filter(user=user, is_active=True)
#     serialized_methods = UserPaymentMethodSerializer(payment_methods, many=True).data

#     # Notifications
#     notifications = Notification.active_objects.filter(
#         user=user,
#         is_read=False,
#         is_active=True
#     ).order_by('-created_at')

#     if notifications.exists():
#         notifications = notifications[:5]
#         for notification in notifications:
#             notification.is_read = True
#             notification.save()

#     # Recent Activity Logs
#     activity_logs = LogEntry.objects.filter(
#         user_id=user.id
#     ).order_by('-action_time')[:6]

#     for log in activity_logs:
#         action_name = log.get_action_flag_display()
#         log.icon_svg = get_icon_for_action(action_name)

#     context = {
#         'user': user,
#         'bot_link': settings.BOT_LINK,
#         'top_channels': top_channels,
#         'active_ad_placements': active_ad_placements,
#         'payment_methods': serialized_methods,
#         'earning': {
#             'available': balance_summary['available'],
#             'locked': balance_summary['locked'],
#             'pending_withdrawals': balance_summary['pending_withdrawals'],
#         },
#         'chart_data': chart_data,
#         'week_labels': week_labels,
#         'notifications': notifications,
#         'activity_logs': activity_logs,
#     }

#     return render(request, 'creator/main.html', context)

# @login_required
@permission_classes([IsCreatorUser])
def dashboard_view(request):
    if request.user.is_authenticated and request.user.user_type == UserType.CREATOR:
        user = request.user
        days = timezone.now().day
        time_threshold = timezone.now() - timezone.timedelta(days=days)

        # Top 3 Channels by Subscribers
        top_channels = CreatorChannel.objects.filter(
            owner=user,
            is_active=True
        ).order_by('-subscribers')[:3]

        # Active Ad Placements
        active_ad_placements = AdPlacement.objects.filter(
            channel__owner=user,
            status__in=['running', 'approved'],
            is_active=True
        ).select_related('ad', 'channel').prefetch_related(
            Prefetch(
                'performance',
                queryset=AdPerformance.objects.filter(date__gte=time_threshold)
            )
        )[:5]

        # Weekly performance data
        weekly_data = AdPerformance.objects.filter(
            ad_placement__channel__owner=user,
            date__gte=time_threshold
        ).values('date__week').annotate(
            total_impressions=Sum('impressions'),
            total_earnings=Sum(F('cost') * 0.85, output_field=DecimalField())
        ).order_by('date__week')

        chart_data = [0, 0, 0, 0]
        week_labels = []

        i = 1
        for i, week_data in enumerate(weekly_data):
            if i < timezone.now().weekday():
                chart_data[i] = float(week_data['total_earnings'] or 0)
                week_number = i+1
                week_labels.append(f"W{week_number}")
                
        # Balance summary
        balance_summary = BalanceService.get_balance_summary(user, role="creator")

        # Payment methods
        payment_methods = UserPaymentMethod.objects.filter(user=user, is_active=True)

        # Notifications (mark as read)
        notifications = Notification.active_objects.filter(
            user=user,
            is_read=False,
            is_active=True
        ).order_by('-created_at')[:5]
        # notifications.update(is_read=True)

        # Recent Activity Logs
        activity_logs = LogEntry.objects.filter(
            user_id=user.id
        ).order_by('-action_time')[:6]

        context = {
            'user': user,
            'bot_link': settings.BOT_LINK,
            'top_channels': top_channels,
            'active_ad_placements': active_ad_placements, 
            'payment_methods': payment_methods,
            'earning': {
                'available': balance_summary['available'],
                'locked': balance_summary['escrow'],
                'pending_withdrawals': balance_summary['pending_withdrawals'],
            },
            'chart_data': chart_data,
            'week_labels': week_labels,
            'notifications': notifications,
            'activity_logs': activity_logs
        }

        return render(request, 'creator/main.html', context)
    return redirect('/')

def get_icon_for_action(action):
    action = action.lower()
    if action == 'addition':
        return '''
        <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
        '''
    elif action == 'deletion':
        return '''
        <svg viewBox="0 0 24 24" width="24" height="24" stroke="#d01277" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
        '''
    elif action == 'change':
        return '''
        <svg viewBox="0 0 24 24" width="24" height="24" stroke="#23c16b" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 20h9"></path>
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
        </svg>
        '''
    else:
        return '''
        <svg viewBox="0 0 24 24" width="24" height="24" stroke="gray" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10" />
        </svg>
        '''