import csv
from django.conf import settings


from django.contrib import admin
from django.contrib import messages
from django.contrib.sessions.models import Session
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME

from allauth.account.models import EmailAddress, EmailConfirmation

from django.db.models import Sum, F, Q, Count, Avg, DecimalField,  ExpressionWrapper, FloatField
from django.db.models.functions import TruncDate

from django.utils import timezone
from django.utils.timezone import now, timedelta
from django.utils.html import format_html
from django.utils.translation import ngettext, gettext_lazy as _
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from rest_framework.authtoken.models import Token
from django.http import HttpResponse, HttpResponseRedirect

# from creator.bot.utils import TelegramPostingUtil

from core.services.matching_engine import CampaignChannelMatcher
from core.services.ad_placement_engine import AdPlacementEngine
from payments.services import WithdrawalService, EarningService

from creators.models import (
    CreatorChannel, 
    CreatorReputation, 
    Category, Language, 
)
from payments.models import (
    Balance,
    Transaction,
    PaymentMethodType, 
    UserPaymentMethod, 
    Escrow, 
    WithdrawalRequest, 
    AuditLog,
)

from core.models import (
    Campaign,
    Ad, 
    AdPlacement, 
    PlacementMatchLog, 
    AdPerformance,
    Currency,
    Notification,
)
from miniapp.models import TelegramVisitorLog

from users.models import TelegramProfile

from core.services.content_delivery_engine import ContentDeliveryService
from core.services.channel_verification_service import verify_creator_channel
from core.utils.notification import send_telegram_notification

from django.urls import path
from django.shortcuts import render
from django.contrib.auth import get_user_model
import json

User = get_user_model()


class AnalyticsAdminSite(admin.AdminSite):
    site_header = "SonicAdz. Admin"
    site_title = "SonicAdz. Admin Portal"
    index_title = "Welcome to SonicAdz. Admin"
    

    def get_urls(self):
        urls = super().get_urls()
        analytics_urls = [
            path('analytics-dashboard/', self.admin_view(self.analytics_dashboard), name='analytics-dashboard'),
            path('analytics-export-csv/', self.admin_view(self.export_csv), name='analytics-export-csv'),
        ]
        return analytics_urls + urls
    
    def export_csv(self, request):
        range_days = int(request.GET.get('range', 30))
        start_date = now() - timedelta(days=range_days)
        export_type = request.GET.get('type', 'default')

        if export_type == 'telegram_visitors':
            visitors = TelegramVisitorLog.objects.filter(timestamp__gte=start_date).order_by('timestamp')
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="telegram_visitors.csv"'
            writer = csv.writer(response)
            writer.writerow([
                'Date',
                'Telegram ID',
                'Username',
                'First Name',
                'Last Name',
                'Is Premium',
                'IP Address',
                'Device Type',
                'OS',
                'Browser',
                'Device Name',
            ])
            for v in visitors:
                writer.writerow([
                    v.timestamp.date(),
                    v.telegram_id,
                    v.username,
                    v.first_name,
                    v.last_name,
                    v.is_premium,
                    v.ip_address,
                    v.device_type,
                    v.os,
                    v.browser,
                    v.device_name,
                ])
            return response

        else:
            # Default export (users & channels as before)
            user_growth = (
                User.objects
                .filter(date_joined__gte=start_date)
                .annotate(date=TruncDate('date_joined'))
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
            )

            channel_trends = (
                CreatorChannel.objects
                .filter(created_at__gte=start_date)
                .annotate(date=TruncDate('created_at'))
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
            )

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="analytics_export.csv"'

            writer = csv.writer(response)
            writer.writerow(['Date', 'New Users', 'New Channels'])

            all_dates = sorted(set(
                [entry['date'] for entry in user_growth] +
                [entry['date'] for entry in channel_trends]
            ))

            users_by_date = {entry['date']: entry['count'] for entry in user_growth}
            channels_by_date = {entry['date']: entry['count'] for entry in channel_trends}

            for date in all_dates:
                writer.writerow([
                    date,
                    users_by_date.get(date, 0),
                    channels_by_date.get(date, 0)
                ])

            return response
    
    def analytics_dashboard(self, request):
        range_days = int(request.GET.get('range', 30))  # default to 30 days
        selected_language = request.GET.get('language')
        selected_range = str(range_days)
        start_date = now() - timedelta(days=range_days)
        
        # User data for bar chart
        user_types = (
            User.objects
            .values('user_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        user_labels = [item['user_type'] for item in user_types]
        user_data = [item['count'] for item in user_types]

        # Category data for pie chart
        categories = (
            Category.objects
            .annotate(channel_count=Count('channels'))
            .order_by('-channel_count')
        )
        category_labels = [cat.name for cat in categories]
        category_data = [cat.channel_count for cat in categories]

        # User growth (line chart)
        user_growth = (
            User.objects
            .filter(date_joined__gte=start_date)
            .annotate(date=TruncDate('date_joined'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        user_growth_labels = [str(entry['date']) for entry in user_growth]
        user_growth_data = [entry['count'] for entry in user_growth]

        # Daily active users (bar chart)
        active_users = (
            User.objects
            .filter(last_login__gte=start_date)
            .annotate(date=TruncDate('last_login'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        daily_active_labels = [str(entry['date']) for entry in active_users]
        daily_active_data = [entry['count'] for entry in active_users]

        # Channels over time (line/area chart)
        channel_trends = (
            CreatorChannel.objects
            .filter(created_at__gte=start_date)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        if selected_language:
            channel_trends = channel_trends.filter(language__in=[selected_language])
        channel_labels = [str(entry['date']) for entry in channel_trends]
        channel_data = [entry['count'] for entry in channel_trends]
        
        # Channel distribution by language
        language_data = (
            Language.objects
            .annotate(channel_count=Count('channels', filter=Q(channels__created_at__gte=start_date)))
            .filter(channel_count__gt=0)
            .order_by('-channel_count')
        )
        language_labels = [lang.name for lang in language_data]
        language_counts = [lang.channel_count for lang in language_data]
        all_languages = Language.objects.filter(is_active=True)
        
        # Payment Methods (Group by PaymentMethodType.name)
        payment_methods = (
            UserPaymentMethod.objects
            .values('payment_method_type__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        payment_method_labels = [item['payment_method_type__name'] for item in payment_methods]
        payment_method_counts = [item['count'] for item in payment_methods]
        
        
        visitor_trends = (
        TelegramVisitorLog.objects
            .filter(timestamp__gte=start_date)
            .annotate(date=TruncDate('timestamp'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        visitor_labels = [str(entry['date']) for entry in visitor_trends]
        visitor_data = [entry['count'] for entry in visitor_trends]

        # Device type distribution
        device_distribution = (
            TelegramVisitorLog.objects
            .values('device_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        device_labels = [d['device_type'] for d in device_distribution]
        device_counts = [d['count'] for d in device_distribution]

        # OS distribution
        os_distribution = (
            TelegramVisitorLog.objects
            .values('os')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        os_labels = [o['os'] for o in os_distribution]
        os_counts = [o['count'] for o in os_distribution]

        # Premium vs Non-premium users
        premium_stats = TelegramVisitorLog.objects.aggregate(
            premium=Count('id', filter=Q(is_premium=True)),
            non_premium=Count('id', filter=Q(is_premium=False)),
        )
        
        # --- Add total audience (reach) over time ---
        range_days = int(request.GET.get('range', 30))
        start_date = now() - timedelta(days=range_days)

        audience_over_time = (
            CreatorChannel.objects
            .filter(created_at__gte=start_date)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(total_reach=Sum('subscribers'))
            .order_by('date')
        )
        
        total_current_reach = CreatorChannel.objects.aggregate(
            total=Sum('subscribers')
        )['total'] or 0

        reach_labels = [str(entry['date']) for entry in audience_over_time]
        reach_data = [entry['total_reach'] or 0 for entry in audience_over_time]
        
        # Add to context
        context = {
            **self.each_context(request),
            'selected_range': selected_range,
            'selected_language': selected_language,
            'title': 'Analytics Dashboard',
            'user_labels': json.dumps(user_labels),      
            'user_data': json.dumps(user_data),
            'user_growth_labels': json.dumps(user_growth_labels),
            'user_growth_data': json.dumps(user_growth_data),
            'category_labels': json.dumps(category_labels),
            'category_data': json.dumps(category_data),
            'daily_active_labels': json.dumps(daily_active_labels),
            'daily_active_data': json.dumps(daily_active_data),
            'channel_labels': json.dumps(channel_labels),
            'channel_data': json.dumps(channel_data),
            'all_languages': all_languages,
            'language_labels': json.dumps(language_labels),
            'language_counts': json.dumps(language_counts),
            'payment_method_labels': json.dumps(payment_method_labels),
            'payment_method_counts': json.dumps(payment_method_counts),
            
            
            'visitor_labels': json.dumps(visitor_labels),
            'visitor_data': json.dumps(visitor_data),
            'device_labels': json.dumps(device_labels),
            'device_counts': json.dumps(device_counts),
            'os_labels': json.dumps(os_labels),
            'os_counts': json.dumps(os_counts),
            'premium_count': premium_stats['premium'],
            'non_premium_count': premium_stats['non_premium'],
            
            'reach_labels': json.dumps(reach_labels),
            'reach_data': json.dumps(reach_data),
            'total_current_reach': total_current_reach,
        }
        return render(request, 'admin/analytics_dashboard.html', context)

# Replace default admin site instance
admin_site = AnalyticsAdminSite(name='sonic_admin')

class TelegramVisitorLogAdmin(admin.ModelAdmin):
    list_display = ['username', 'is_premium', 'device_type', 'os', 'device_name', 'timestamp']
    search_fields = ['device_name', 'ip_address', 'username', 'first_name', 'last_name', 'telegram_id']

    def get_readonly_fields(self, request, obj=None):
        # Automatically make all model fields readonly
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False  # Optional: disable adding via admin

    def has_change_permission(self, request, obj=None):
        return False  # Optional: disable editing via admin
    
admin_site.register(TelegramVisitorLog, TelegramVisitorLogAdmin)
class TelegramProfileInline(admin.TabularInline):
    model = TelegramProfile
    extra = 0
    
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'address', 'user_type')}),
        (('Verification & Last Seen'), {'fields': ('email_verified', 'phone_verified')}), # Removed 'last_seen'
        (('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    list_display = (
        'username',
        'phone_number',
        'user_type',
        'is_staff',
        'is_active',
        'phone_verified',
        'email_verified',
        'last_seen', 
    )

    search_fields = (
        'username',
        'first_name',
        'last_name',
        'email',
        'phone_number',
    )
    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        'user_type',
        'email_verified',
        'phone_verified',
    )
    
    readonly_fields = ('last_login', 'date_joined', 'last_seen')

    inlines = [TelegramProfileInline]
    actions = ['activate_users', 'deactivate_users', 'reset_user_sessions']
    
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} users activated.")

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} users deactivated.")
        
    def reset_user_sessions(self, request, queryset):
        from django.contrib.sessions.models import Session
        sessions = Session.objects.all()
        count = 0

        for session in sessions:
            data = session.get_decoded()
            if data.get('_auth_user_id') and int(data.get('_auth_user_id')) in queryset.values_list('id', flat=True):
                session.delete()
                count += 1

        self.message_user(
            request,
            ngettext(
                'Reset session for %(count)d user.',
                'Reset sessions for %(count)d users.',
                count
            ) % {'count': count},
            messages.SUCCESS
        )
    reset_user_sessions.short_description = "Reset sessions for selected users"
    
admin_site.register(User, UserAdmin)

class EmailAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'verified', 'primary')
    search_fields = ('email', 'user__username')

admin_site.register(EmailAddress, EmailAddressAdmin)

class EmailConfirmationAdmin(admin.ModelAdmin):
    list_display = ('email_address', 'created', 'sent', 'key')
    search_fields = ('email_address__email',)

admin_site.register(EmailConfirmation, EmailConfirmationAdmin)

class SessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'user', 'expire_date', 'is_expired')
    actions = ['delete_selected']

    def user(self, obj):
        try:
            data = obj.get_decoded()
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_id = data.get('_auth_user_id')
            if user_id:
                user = User.objects.get(id=user_id)
                url = reverse('admin:users_user_change', args=[user_id])
                return format_html('<a href="{}">{}</a>', url, user)
        except Exception:
            return "-"
        return "-"

    def is_expired(self, obj):
        return obj.expire_date < now()
    is_expired.boolean = True

admin_site.register(Session, SessionAdmin)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'user', 'created')
    search_fields = ('user__username',)

admin_site.register(Token, TokenAdmin)

class CreatorReputationInline(admin.TabularInline):
    model = CreatorReputation
    extra = 0
    
    fields = (
        'rating', 
        'fraud_score', 
        'total_complaints', 
        'last_reviewed', 
        'avg_engagement_rate',
        'estimated_views_avg',
        'estimated_views_max',
        'estimated_cost_min',
        'estimated_cost_max',
    )
    
    readonly_fields = (
        'rating',
        'avg_engagement_rate',
        'estimated_views_avg',
        'estimated_views_max',
        'estimated_cost_min',
        'estimated_cost_max',
    )
 
class CreatorChannelAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'subscribers', 
        'min_cpm',
        'region', 
        'status', 
        'is_active', 
        'created_at'
    )
    list_filter = ('status', 'is_active', 'region', 'created_at')
    search_fields = ('title', 'owner__username', 'channel_link', 'cpm')
    filter_horizontal = ('language', 'category')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('owner',)
    inlines = [CreatorReputationInline]
    
    list_filter = (
        'status', 
        'is_active', 
        'region', 
        'created_at',
        'reputation__rating', 
        'category',         
    )
     
    actions = ['generate_portfolio_summary', 
               'verify_channels_admin_action', 
               'notify_missing_payment_methods', 
               'bulk_message_channel_owners'
               ]
    


    def generate_portfolio_summary(self, request, queryset):
        """
        Generates a detailed financial report per selected channel, including average cost
        and optional category breakdown.
        """
        if not queryset.exists():
            self.message_user(request, "No channels were selected for the report.", level='warning')
            return

        # Only channels with reputation data
        annotated_queryset = queryset.filter(reputation__isnull=False).annotate(
            min_cost=F('reputation__estimated_cost_min'),
            max_cost=F('reputation__estimated_cost_max'),
            avg_cost=ExpressionWrapper(
                (F('reputation__estimated_cost_min') + F('reputation__estimated_cost_max')) / 2,
                output_field=FloatField()
            ),
            avg_er=F('reputation__avg_engagement_rate'),
            avg_rating=F('reputation__rating'),
            views_avg=F('reputation__estimated_views_avg'),
            views_max=F('reputation__estimated_views_max'),
        ).select_related('owner')

        # Create the summary list
        channel_summary = annotated_queryset.values(
            'title',
            'owner__username',
            'pp_url',
            'subscribers',
            'min_cost',
            'max_cost',
            'avg_cost',
            'avg_er',
            'avg_rating',
            'views_avg',
            'views_max',
            'channel_link',
        ).order_by('-max_cost')  # Show high-potential channels first

        # Totals
        grand_total_min_cost = sum(row['min_cost'] for row in channel_summary if row['min_cost'] is not None)
        grand_total_max_cost = sum(row['max_cost'] for row in channel_summary if row['max_cost'] is not None)

        # Optional category breakdown
        category_counts = queryset.values('category__name').annotate(count=Count('id')).order_by('-count')
        formatted_categories = [
            {"category": row["category__name"] or "Uncategorized", "count": row["count"]}
            for row in category_counts
        ]

        context = dict(
            self.admin_site.each_context(request),
            title="Channel Financial Breakdown Report",
            summary=list(channel_summary),
            grand_min=grand_total_min_cost,
            grand_max=grand_total_max_cost,
            selected_count=annotated_queryset.count(),
            action_count=queryset.count(),
            category_data=formatted_categories,
        )

        return TemplateResponse(request, "admin/channel_portfolio_summary.html", context)
    generate_portfolio_summary.short_description = " Generate Portfolio Summary Report"
    
    
    
    def verify_channels_admin_action(self, request, queryset):
        failed = 0
        success = 0

        for channel in queryset:
            if verify_creator_channel(channel):
                success += 1
            else:
                failed += 1

        self.message_user(
            request,
            f"Verification complete. Verified: {success}, Unverified: {failed}",
            messages.SUCCESS if failed == 0 else messages.WARNING
        )

    verify_channels_admin_action.short_description = "🔍 Verify Bot Admin Status for Selected Channels"

    def notify_missing_payment_methods(self, request, queryset):
        """
        Sends a notification and Telegram message to creators who don't have a verified payment method.
        Only applies to verified channels.
        """
        notified = 0
        skipped = 0

        for channel in queryset:
            if channel.status != 'verified':
                skipped += 1
                continue

            owner = channel.owner
            has_verified_payment = UserPaymentMethod.objects.filter(
                user=owner,
                status=UserPaymentMethod.Status.VERIFIED
            ).exists()

            if has_verified_payment:
                continue

            # Send notification
            Notification.objects.create(
                user=owner,
                title="⚠️ Add a Verified Payment Method",
                message="You're verified but still missing a verified payment method. Please add one to start earning.",
                type="Payment"
            )

            # Send Telegram message if applicable
            if hasattr(owner, 'telegram_profile') and owner.telegram_profile.chat_id:
                send_telegram_notification(
                    chat_id=owner.telegram_profile.chat_id,
                    text=(
                        "⚠️ Verify Payment Method!\n\n"
                        "You're missing a verified *payment method*. "
                        "Please add one to be eligible for payouts."
                    )
                )

            notified += 1

        self.message_user(
            request,
            f"Notification sent to {notified} creator(s). Skipped {skipped} unverified channel(s).",
            messages.SUCCESS
        )

    notify_missing_payment_methods.short_description = "💸 Notify Creators Without Verified Payment Method"
    
    def bulk_message_channel_owners(self, request, queryset):
        """
        Send bulk messages to selected channel owners with custom or default messages.
        """        
        if request.method == 'POST' and 'apply' in request.POST:
           
            
            # Process the form submission
            message_type = request.POST.get('message_type')
            custom_message = request.POST.get('custom_message', '').strip()
            notification_title = request.POST.get('notification_title', '').strip()
          
            
            notified = 0
            skipped = 0
            errors = []
            
            # Define default messages
            default_messages = {
                'welcome': {
                    'title': '👋 Welcome to Our Platform!',
                    'message': 'Welcome to our creator platform! We\'re excited to have you onboard. Start by completing your profile and exploring campaign opportunities.',
                    'telegram': '👋 *Welcome to Our Platform!*\n\nWe\'re excited to have you onboard! Start by completing your profile and exploring campaign opportunities.'
                },
                'campaign_opportunity': {
                    'title': '🎯 New Campaign Opportunity',
                    'message': 'Great news! New campaign opportunities are available that match your channel. Check your dashboard for details.',
                    'telegram': '🎯 *New Campaign Opportunity!*\n\nGreat news! New campaigns matching your channel are available. Check your dashboard for details.'
                },
                'payment_reminder': {
                    'title': '💰 Payment Method Reminder',
                    'message': 'Please ensure your payment method is verified to receive payouts for completed campaigns.',
                    'telegram': '💰 *Payment Method Reminder*\n\nPlease verify your payment method to receive payouts for completed campaigns.'
                },
                'performance_update': {
                    'title': '📊 Your Performance Update',
                    'message': 'Your channel performance is looking great! Keep up the good work and consider optimizing your content for better engagement.',
                    'telegram': '📊 *Performance Update*\n\nYour channel is performing well! Consider optimizing content for even better engagement.'
                },
                'platform_update': {
                    'title': '🆕 Platform Updates',
                    'message': 'We\'ve recently updated our platform with new features. Check out the latest improvements in your dashboard.',
                    'telegram': '🆕 *Platform Updates*\n\nWe\'ve added new features! Check your dashboard for the latest improvements.'
                }
            }
            
            # Validate message type
            if not message_type:
                self.message_user(
                    request,
                    "Please select a message type.",
                    messages.ERROR
                )
                return HttpResponseRedirect(request.get_full_path())
            
            # Determine which message to use
            if message_type == 'custom':
                if not custom_message:
                    self.message_user(
                        request,
                        "Please provide a custom message.",
                        messages.ERROR
                    )
                    return HttpResponseRedirect(request.get_full_path())
                title = notification_title or "📢 Message from Platform"
                message = custom_message
                telegram_message = custom_message
            elif message_type in default_messages:
                title = default_messages[message_type]['title']
                message = default_messages[message_type]['message']
                telegram_message = default_messages[message_type]['telegram']
            else:
                self.message_user(
                    request,
                    "Please select a valid message type.",
                    messages.ERROR
                )
                return HttpResponseRedirect(request.get_full_path())
            
            # Send messages to selected channels
            for channel in queryset:
                try:
                    owner = channel.owner
                                        
                    # Create notification
                    notification = Notification.objects.create(
                        user=owner,
                        title=title,
                        message=message,
                        type="Admin Message"
                    )
                    
                    # Send Telegram message if available
                    telegram_sent = False
                    if hasattr(owner, 'telegram_profile') and owner.telegram_profile.tg_id:
                        try:
                            send_telegram_notification(
                                chat_id=owner.telegram_profile.tg_id,
                                text=telegram_message
                            )
                            telegram_sent = True
                        except Exception as e:
                            error_msg = f"Telegram failed for {owner}: {str(e)}"
                            errors.append(error_msg)
                    else:
                        print(f"DEBUG: No Telegram profile or tg_id for {owner}")
                    
                    notified += 1
                    
                except Exception as e:
                    error_msg = f"Failed for {channel.title}: {str(e)}"
                    errors.append(error_msg)
                    skipped += 1

            
            # Show results
            success_message = f"Messages sent to {notified} channel owner(s)."
            if skipped:
                success_message += f" {skipped} failed."
            
            if errors:
                self.message_user(request, "Some errors occurred:", messages.WARNING)
                for error in errors[:5]:  # Show first 5 errors
                    self.message_user(request, f"• {error}", messages.WARNING)
                if len(errors) > 5:
                    self.message_user(request, f"... and {len(errors) - 5} more errors.", messages.WARNING)
            
            self.message_user(request, success_message, messages.SUCCESS)
            return HttpResponseRedirect(request.get_full_path())
        
        from django.shortcuts import render
        return render(request, 'admin/bulk_message_channel_owners.html', {
            'channels': queryset,
            'title': 'Bulk Message Channel Owners',
            'action': 'bulk_message_channel_owners',
        })

    bulk_message_channel_owners.short_description = "📨 Send Bulk Message to Channel Owners"
    
admin_site.register(CreatorChannel, CreatorChannelAdmin)


# ============== MODEL ADMINS ==============

class AdInline(admin.TabularInline):
    model = Ad
    extra = 0
    fields = ('headline', 'text_content', 'img_url', 'is_active', 'ml_score')
    readonly_fields = ('ml_score',)
    show_change_link = True

class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'advertiser_link', 'objective', 'status_badge', 
                    'initial_budget', 'total_spent', 'start_date', 'end_date', 
                    'is_active')
    list_filter = ('objective', 'status', 'is_active', 'start_date')
    search_fields = ('name', 'advertiser__username', 'advertiser__email')
    list_select_related = ('advertiser',)
    list_per_page = 25
    inlines = [AdInline]
    actions = ['approve_campaigns', 'pause_campaigns', 'resubmit_campaigns']
    readonly_fields = ('total_spent', 'created_at', 'updated_at')
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('advertiser', 'name', 'objective', 'status', 'admin_notes')
        }),
        (_('Budget & Targeting'), {
            'fields': ('initial_budget', 'total_spent', 'cpm', 
                      ('start_date', 'end_date'), 'views_frequency_cap',
                      'targeting_languages', 'targeting_regions', 
                      'targeting_categories')
        }),
        (_('Status & Metadata'), {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    filter_horizontal = ('targeting_languages', 'targeting_categories')
    autocomplete_fields = ['advertiser']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('advertiser')

    def status_badge(self, obj):
        status_colors = {
            'draft': 'bg-secondary',
            'in_review': 'bg-warning text-dark',
            'scheduled': 'bg-primary',
            'active': 'bg-success',
            'on_hold': 'bg-info text-dark',
            'stopped': 'bg-danger',
            'declined': 'bg-dark',
            'completed': 'bg-secondary',
        }
        return format_html(
            '<span class="badge {}">{}</span>',
            status_colors.get(obj.status, 'bg-secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def advertiser_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.advertiser.id])
        return format_html('<a href="{}">{}</a>', url, obj.advertiser.username)
    advertiser_link.short_description = 'Advertiser'
    advertiser_link.admin_order_field = 'advertiser__username'

    @admin.action(description='Approve selected campaigns')
    def approve_campaigns(self, request, queryset):
        updated = 0
        for campaign in queryset.filter(status='in_review'):
            if not campaign.ads.filter(is_active=True).exists():
                self.message_user(
                    request,
                    f"Campaign '{campaign.name}' has no active ads.",
                    messages.WARNING
                )
                continue
            campaign.status = 'active'  # Signal will handle activation and posting
            campaign.save()
            advertiser = campaign.advertiser        
            advertiser_title = f"Ad Placement {campaign.status.title()}"
            advertiser_message = (
                f"Your ad '{campaign.ads.first()}' in campaign '{campaign.name}' "
                f"has been Approved and is now Live"
            )
            Notification.objects.create(
                user=advertiser,
                title=advertiser_title,
                message=advertiser_message,
                type='campaign_approved'
            )
            updated += 1
        self.message_user(
            request,
            f'Successfully approved {updated} campaigns.',
            messages.SUCCESS
        )
        

    @admin.action(description='Pause selected campaigns')
    def pause_campaigns(self, request, queryset):
        updated = queryset.filter(status='active').update(status='on_hold')
        for campaign in queryset.filter(status='active'):
            AdPlacement.objects.filter(ad__campaign=campaign).update(status='paused')
        self.message_user(
            request,
            f'Successfully paused {updated} campaigns.',
            messages.SUCCESS
        )

    @admin.action(description='Resubmit selected campaigns')
    def resubmit_campaigns(self, request, queryset):
        updated = queryset.filter(status__in=['declined', 'stopped']).update(status='in_review')
        for campaign in queryset.filter(status__in=['declined', 'stopped']):
            top_matches = CampaignChannelMatcher(campaign).get_ranked_channels(top_n=25)
            AdPlacementEngine(campaign, top_matches).assign_placements()
        self.message_user(
            request,
            f'Successfully resubmitted {updated} campaigns for review.',
            messages.SUCCESS
        )

    def get_object_actions(self, request, context, **kwargs):
        actions = []
        obj = context.get('original')
        if obj:
            if obj.status == 'in_review':
                actions.append(('approve', 'Approve Campaign'))
                actions.append(('decline', 'Decline Campaign'))
            elif obj.status == 'active':
                actions.append(('pause', 'Pause Campaign'))
            elif obj.status in ['declined', 'stopped']:
                actions.append(('resubmit', 'Resubmit for Review'))
            elif obj.status == 'on_hold':
                actions.append(('resume', 'Resume Campaign'))
        return actions

    def approve(self, request, obj):
        if not obj.ads.filter(is_active=True).exists():
            self.message_user(
                request,
                f"Campaign '{obj.name}' has no active ads.",
                messages.WARNING
            )
            return HttpResponseRedirect(request.path)
        obj.status = 'active'  # Signal will handle activation and posting
        obj.save()
        self.message_user(request, 'Campaign approved successfully.', messages.SUCCESS)
        return HttpResponseRedirect(request.path)

    def decline(self, request, obj):
        obj.status = 'declined'
        obj.admin_notes = f"Declined on {timezone.now().date()}: {obj.admin_notes or 'No notes provided'}"
        obj.save()
        self.message_user(request, 'Campaign declined.', messages.WARNING)
        return HttpResponseRedirect(request.path)

    def pause(self, request, obj):
        obj.status = 'on_hold'
        obj.save()
        AdPlacement.objects.filter(ad__campaign=obj).update(status='paused')
        self.message_user(request, 'Campaign paused.', messages.INFO)
        return HttpResponseRedirect(request.path)

    def resume(self, request, obj):
        obj.status = 'active'  # Signal will handle activation and posting
        obj.save()
        self.message_user(request, 'Campaign resumed.', messages.SUCCESS)
        return HttpResponseRedirect(request.path)

    def resubmit(self, request, obj):
        top_matches = CampaignChannelMatcher(obj).get_ranked_channels(top_n=25)
        AdPlacementEngine(obj, top_matches).assign_placements()
        obj.status = 'in_review'
        obj.save()
        self.message_user(request, 'Campaign resubmitted for review.', messages.SUCCESS)
        return HttpResponseRedirect(request.path)

    class Media:
        css = {
            'all': ['css/admin-badges.css']
        }
        
admin_site.register(Campaign, CampaignAdmin)

class AdAdmin(admin.ModelAdmin):
    list_display = ('headline', 'campaign', 'ml_score', 
                    'is_active', 'created_at')
    list_filter = ('is_active', 'campaign__status', 'created_at')
    search_fields = ('headline', 'text_content', 'campaign__name')
    list_select_related = ('campaign',)
    raw_id_fields = ('campaign',)
    readonly_fields = ('ml_score', 'created_at', 'updated_at')
    fieldsets = (
        (_('Ad Details'), {
            'fields': ('campaign', 'headline', 'text_content', 'img_url', 'social_links', 'brand_name')
        }),
        (_('Performance Metrics'), {
            'fields': ('ml_score',)
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def campaign_link(self, obj):
        url = reverse('admin:advertising_campaign_change', args=[obj.campaign.id])
        return format_html('<a href="{}">{}</a>', url, obj.campaign.name)
    campaign_link.short_description = 'Campaign'
    campaign_link.admin_order_field = 'campaign__name'
    
    def ml_score_badge(self, obj):
        color = 'bg-success' if obj.ml_score > 0.7 else 'bg-warning' if obj.ml_score > 0.4 else 'bg-danger'
        return format_html(
            '<span class="badge {}">{:.2f}</span>',
            color,
            obj.ml_score
        )
    ml_score_badge.short_description = 'ML Score'
    ml_score_badge.admin_order_field = 'ml_score'
    
    class Media:
        css = {
            'all': ['css/admin-badges.css']
        }
admin_site.register(Ad, AdAdmin)

class AdPerformanceInline(admin.TabularInline):
    model = AdPerformance
    extra = 0
    readonly_fields = ('date', 'impressions', 'clicks', 'conversions', 'cost', 
                      'ctr', 'cpc', 'conversion_rate')
    fields = ('date', 'impressions', 'clicks', 'conversions', 'cost', 
             'ctr', 'cpc', 'conversion_rate')
    
    def ctr(self, obj):
        return f"{obj.ctr:.2f}%"
    ctr.short_description = 'CTR'
    
    def cpc(self, obj):
        return f"${obj.cpc:.2f}"
    cpc.short_description = 'CPC'
    
    
    def conversion_rate(self, obj):
        return f"{obj.conversion_rate:.2f}%"
    conversion_rate.short_description = 'Conv. Rate'
    
class PlacementMatchLogAdmin(admin.ModelAdmin):
    list_display = ('campaign_name', 'channel', 'ad_headline', 'estimated_cost', 'matched_on', 'reason_summary')
    list_filter = ('matched_on',)
    search_fields = ('campaign__name', 'ad_placement__channel__title', 'ad_placement__ad__headline', 'reason')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('campaign', 'ad_placement', 'ad_placement__ad', 'ad_placement__channel')

    def campaign_name(self, obj):
        return obj.campaign.name
    campaign_name.short_description = 'Campaign'

    def channel(self, obj):
        return obj.ad_placement.channel.title
    channel.admin_order_field = 'ad_placement__channel__title'

    def ad_headline(self, obj):
        return obj.ad_placement.ad.headline
    ad_headline.admin_order_field = 'ad_placement__ad__headline'

    def reason_summary(self, obj):
        return obj.reason[:75] + ('...' if len(obj.reason) > 75 else '')
    reason_summary.short_description = 'Reason'

admin_site.register(PlacementMatchLog, PlacementMatchLogAdmin)

class PlacementMatchLogInline(admin.TabularInline):
    model = PlacementMatchLog
    extra = 0
    readonly_fields = ('campaign', 'matched_on', 'estimated_cost', 'reason', 'created_at')
    can_delete = False
    
        

class AdPlacementAdmin(admin.ModelAdmin):
    list_display = ('ad_headline', 'channel_link', 'status_badge', 
                    'preference_score', 'is_active', 'placed_at')
    list_filter = ('status', 'is_active', 'placed_at')
    search_fields = ('ad__headline', 'channel__title', 'id')
    list_select_related = ('ad__campaign', 'channel')
    raw_id_fields = ('ad', 'channel')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-placed_at',)
    inlines = [AdPerformanceInline, PlacementMatchLogInline]

    actions = ['post_new_placements', 'repost_placements', 'stop_placements'] 

    def post_new_placements(self, request, queryset):
        bot_token = getattr(settings, "BOT_SECRET_TOKEN", None)
        if not bot_token:
            self.message_user(request, "Bot token not configured", level=messages.ERROR)
            return

        service = ContentDeliveryService(bot_token)
        success_count = 0
        skip_count = 0

        for placement in queryset:
            if placement.status in ['running']:
                skip_count += 1
                continue  # Skip already posted placements

            result = service.post_to_channel(placement)
            if result.get("success"):
                success_count += 1
            else:
                self.message_user(
                    request,
                    f"Failed to post placement {placement.id} ({placement.channel.title}): {result.get('error')}",
                    level=messages.WARNING
                )

        if success_count > 0:
            self.message_user(
                request,
                f"Successfully posted {success_count} new placements to Telegram.",
                level=messages.SUCCESS
            )
        if skip_count > 0:
            self.message_user(
                request,
                f"Skipped {skip_count} placements already marked as running or completed.",
                level=messages.INFO
            )

    post_new_placements.short_description = "📤 Post New Placements to Telegram"
    

    def repost_placements(self, request, queryset):
        bot_token = getattr(settings, "BOT_SECRET_TOKEN", None)
        if not bot_token:
            self.message_user(request, "Bot token not configured", level=messages.ERROR)
            return

        service = ContentDeliveryService(bot_token)
        success_count = 0

        for placement in queryset:
            result = service.remove_and_repost(placement)
            if result.get("success"):
                success_count += 1
            else:
                self.message_user(
                    request,
                    f"Failed to repost placement {placement.id}: {result.get('error')}",
                    level=messages.WARNING
                )

        self.message_user(request, f"Successfully reposted {success_count} placements.")

    repost_placements.short_description = "🔂 Repost Selected Placements to Telegram"


    def stop_placements(self, request, queryset):
        bot_token = getattr(settings, "BOT_SECRET_TOKEN", None)
        if not bot_token:
            self.message_user(request, "Bot token not configured", level=messages.ERROR)
            return

        service = ContentDeliveryService(bot_token)
        success_count = 0

        for placement in queryset:
            result = service.delete_from_channel(placement)
            if result.get("success"):
                success_count += 1
            else:
                self.message_user(
                    request,
                    f"Failed to stop placement {placement.id}: {result.get('error')}",
                    level=messages.WARNING
                )

        self.message_user(request, f"Successfully stopped {success_count} placements.")

    stop_placements.short_description = "🛑 Stop & Delete Selected Placements from Telegram"
    
    
    def ad_headline(self, obj):
        return obj.ad.headline
    ad_headline.short_description = 'Ad Headline'
    ad_headline.admin_order_field = 'ad__headline'

    def channel_link(self, obj):
        url = reverse('admin:creators_creatorchannel_change', args=[obj.channel.id])
        return format_html('<a href="{}">{}</a>', url, obj.channel.title)
    channel_link.short_description = 'Channel'
    channel_link.admin_order_field = 'channel__title'

    def status_badge(self, obj):
        status_colors = {
            'draft': 'bg-secondary',
            'pending': 'bg-warning text-dark',
            'approved': 'bg-success',
            'rejected': 'bg-danger',
            'paused': 'bg-info text-dark',
            'completed': 'bg-primary',
        }
        return format_html(
            '<span class="badge {}">{}</span>',
            status_colors.get(obj.status, 'bg-secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    class Media:
        css = {
            'all': ['css/admin-badges.css']
        }

admin_site.register(AdPlacement, AdPlacementAdmin)

class AdPerformanceAdmin(admin.ModelAdmin):
    list_display = ('date', 'ad_placement_link', 'impressions', 'clicks', 
                    'ctr', 'cost', 'conversion_rate', 'time_delta', 'timestamp')
    list_filter = ('date', 'ad_placement__status')
    search_fields = ('ad_placement__ad__headline', 'ad_placement__channel__title', 'id')
    readonly_fields = ('ctr', 'cpc', 'conversion_rate', 'engagement_rate',
                      'soft_ctr', 'viewability_rate', 'virality_rate')
    list_select_related = ('ad_placement__ad', 'ad_placement__channel')
    
    def ad_placement_link(self, obj):
        url = reverse('admin:core_adplacement_change', args=[obj.ad_placement.id])
        return format_html('<a href="{}">{} → {}</a>', 
                         url, 
                         obj.ad_placement.ad.headline,
                         obj.ad_placement.channel.title)
    ad_placement_link.short_description = 'Ad Placement'
    
    def ctr(self, obj):
        return f"{obj.ctr:.2f}%"
    ctr.short_description = 'CTR'
    ctr.admin_order_field = 'ctr'
    
    def conversion_rate(self, obj):
        return f"{obj.conversion_rate:.2f}%"
    conversion_rate.short_description = 'Conv. Rate'
    conversion_rate.admin_order_field = 'conversion_rate'
admin_site.register(AdPerformance, AdPerformanceAdmin)


class PaymentMethodTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'logo_preview', 'is_active']
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" height="30"/>', obj.logo)
        return "—"
    
    logo_preview.short_description = "Logo"

    actions = ['activate_methods', 'deactivate_methods']

    def activate_methods(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} payment method(s) activated.", messages.SUCCESS)

    activate_methods.short_description = "🔓 Activate selected payment methods"

    def deactivate_methods(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} payment method(s) deactivated.", messages.WARNING)

    deactivate_methods.short_description = "🔒 Deactivate selected payment methods"
   
admin_site.register(PaymentMethodType, PaymentMethodTypeAdmin)
 
class UserPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('account_name', 'payment_method_type', 'status', 'is_default', 'is_active')
    list_filter = ('payment_method_type', 'status', 'is_default', 'is_active')
    search_fields = ('user__username', 'account_name')
    list_select_related = ('user',)

    actions = [
        'verify_methods',
        'reject_methods',
        'activate_methods',
        'deactivate_methods',
    ]

    DEFAULT_REJECTION_REASON = (
        "Your payment method was rejected. Please make sure all information is correct and try again."
    )

    def verify_methods(self, request, queryset):
        valid_methods = queryset.filter(status__in=[
            UserPaymentMethod.Status.PENDING,
            UserPaymentMethod.Status.REJECTED
        ])

        updated_count = 0

        for method in valid_methods:
            has_verified_default = UserPaymentMethod.objects.filter(
                user=method.user,
                status=UserPaymentMethod.Status.VERIFIED,
                is_default=True
            ).exists()

            method.status = UserPaymentMethod.Status.VERIFIED
            method.is_active = True
            method.is_default = not has_verified_default
            method.save()
            updated_count += 1

        self.message_user(
            request,
            f"{updated_count} payment method(s) marked as VERIFIED (and default if needed).",
            messages.SUCCESS
        )

    verify_methods.short_description = "✅ Verify selected payment methods (auto-default if needed)"
    

    def reject_methods(self, request, queryset):
        from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
        from payments.forms.admin_form import RejectPaymentMethodForm

        # Only allow pending or verified ones to be rejected
        valid_queryset = queryset.filter(status__in=[
            UserPaymentMethod.Status.PENDING,
            UserPaymentMethod.Status.VERIFIED
        ])

        if 'apply' in request.POST:
            form = RejectPaymentMethodForm(request.POST)

            if form.is_valid():
                reason = form.cleaned_data['rejection_reason'].strip() or self.DEFAULT_REJECTION_REASON
                selected_ids = request.POST.getlist('_selected_action')
                methods = valid_queryset.filter(id__in=selected_ids)

                for method in methods:
                    method.status = UserPaymentMethod.Status.REJECTED
                    method.is_default = False
                    method.save()

                    method_info = f"{method.payment_method_type.name} ({method.get_display_reference()})"

                    # Create internal notification
                    Notification.objects.create(
                        user=method.user,
                        title="Payment Method Rejected",
                        message=f"❌ Your payment method *{method_info}* was rejected. Please review and submit a valid one.",
                        type="custom"
                    )

                    tg_profile = getattr(method.user, 'telegram_profile', None)
                    if tg_profile and tg_profile.tg_id:
                        send_telegram_notification(
                            chat_id=tg_profile.tg_id,
                            text=(
                                f"❌ *Payment Method Rejected*\n\n"
                                f"Your payment method *{method_info}* was rejected.\n"
                                "Please review and submit a valid one."
                            )
                        )

                self.message_user(request, f"{methods.count()} payment method(s) rejected and users notified.", messages.WARNING)
                return redirect(request.get_full_path())

        else:
            form = RejectPaymentMethodForm(initial={
                '_selected_action': request.POST.getlist(ACTION_CHECKBOX_NAME)
            })

        return render(request, 'admin/reject_payment_methods.html', {
            'form': form,
            'methods': valid_queryset,
            'title': 'Reject Selected Payment Methods',
        })

    reject_methods.short_description = "❌ Reject selected payment methods (only pending/verified)"

    def activate_methods(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} payment method(s) activated.", messages.SUCCESS)

    activate_methods.short_description = "🔓 Activate selected payment methods"

    def deactivate_methods(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} payment method(s) deactivated.", messages.WARNING)

    deactivate_methods.short_description = "🔒 Deactivate selected payment methods"

admin_site.register(UserPaymentMethod, UserPaymentMethodAdmin)

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'sub_balance', 'after_balance', 'transaction_reference', 'timestamp')
    list_filter = ('transaction_type', 'sub_balance')
    search_fields = ('user__username', 'transaction_reference')
    readonly_fields = ('id', 'user', 'transaction_type', 'amount', 'sub_balance', 'after_balance', 'transaction_reference', 'timestamp')
    ordering = ['-timestamp']
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    
admin_site.register(Transaction, TransactionAdmin)

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    fields = ('transaction_type', 'amount', 'sub_balance', 'after_balance', 'transaction_reference', 'timestamp')
    readonly_fields = ('id', 'user', 'transaction_type', 'amount', 'sub_balance', 'after_balance', 'transaction_reference', 'timestamp')
    can_delete = True
    show_change_link = True
    ordering = ['-timestamp']

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj=None):
        return False
    

class BalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'available', 'escrow', 'pending_withdrawals', 'total')
    list_filter = ('type',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at', 'total')
    inlines = [TransactionInline]
    actions = ['release_escrow_for_creators']

    def release_escrow_for_creators(self, request, queryset):
        released_count = 0
        total_amount = 0
        for balance in queryset:
            if balance.type != 'creator' or balance.escrow <= 0:
                continue  # Skip non-creators or zero escrow
            try:
                amount = EarningService.release_earnings(balance.user)
                released_count += 1
                total_amount += amount
            except ValueError as e:
                self.message_user(request, f"Failed to release for {balance.user}: {e}", level=messages.ERROR)
        if released_count > 0:
            self.message_user(request, f"Released escrow for {released_count} creators totaling {total_amount}.", level=messages.SUCCESS)
        else:
            self.message_user(request, "No valid creators with escrow to release.", level=messages.WARNING)

    release_escrow_for_creators.short_description = "Release escrow to available balance for selected creators"
    
admin_site.register(Balance, BalanceAdmin)

class EscrowAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'advertiser_username',
        'campaign_name',
        'amount',
        'remaining_amount',
        'status_badge',
        'created_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'advertiser__username', 'campaign__name')
    list_select_related = ('advertiser', 'campaign')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    def advertiser_username(self, obj):
        return obj.advertiser.username
    advertiser_username.short_description = 'Advertiser'
    advertiser_username.admin_order_field = 'advertiser__username'

    def campaign_name(self, obj):
        return obj.campaign.name if obj.campaign else "-"
    campaign_name.short_description = 'Campaign'

    def status_badge(self, obj):
        status_colors = {
            'cancelled': 'bg-danger',
            'released': 'bg-success',
            'pending': 'bg-warning text-dark',
        }
        return format_html(
            '<span class="badge {}">{}</span>',
            status_colors.get(obj.status, 'bg-secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def get_queryset(self, request):
        # Optimize queryset with select_related
        return super().get_queryset(request).select_related('advertiser', 'campaign')

    class Media:
        css = {
            'all': ['css/admin-badges.css']
        }
admin_site.register(Escrow, EscrowAdmin)


class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_payment_method', 'amount', 'status', 'reference', 'created_at', 'approved_at', 'completed_at')
    list_filter = ('status', 'created_at', 'approved_at', 'completed_at',)
    search_fields = ('user_payment_method__user__username', 'reference')
    readonly_fields = ('id', 'user_payment_method', 'amount', 'reference', 'created_at', 'approved_at', 'completed_at')
    list_select_related = ('user_payment_method__user',)
    ordering = ['created_at']
    actions = ['approve_withdrawals', 'reject_withdrawals', 'complete_withdrawals']

    def approve_withdrawals(self, request, queryset):
        approved_count = 0
        for withdrawal in queryset.filter(status='pending'):
            try:
                WithdrawalService.approve_withdrawal(withdrawal.id, request.user)
                approved_count += 1
            except ValueError as e:
                self.message_user(request, f"Failed to approve {withdrawal.id}: {e}", level=messages.ERROR)
        if approved_count > 0:
            self.message_user(request, f"Approved {approved_count} withdrawal requests.", level=messages.SUCCESS)
        else:
            self.message_user(request, "No pending withdrawals to approve.", level=messages.WARNING)

    approve_withdrawals.short_description = "Approve selected pending withdrawals"

    def reject_withdrawals(self, request, queryset):
        rejected_count = 0
        for withdrawal in queryset.filter(status='pending'):
            try:
                WithdrawalService.reject_withdrawal(withdrawal.id, request.user)
                rejected_count += 1
            except ValueError as e:
                self.message_user(request, f"Failed to reject {withdrawal.id}: {e}", level=messages.ERROR)
        if rejected_count > 0:
            self.message_user(request, f"Rejected {rejected_count} withdrawal requests.", level=messages.SUCCESS)
        else:
            self.message_user(request, "No pending withdrawals to reject.", level=messages.WARNING)

    reject_withdrawals.short_description = "Reject selected pending withdrawals"

    def complete_withdrawals(self, request, queryset):
        completed_count = 0
        for withdrawal in queryset.filter(status='approved'):
            try:
                WithdrawalService.complete_withdrawal(withdrawal.id, request.user)
                completed_count += 1
            except ValueError as e:
                self.message_user(request, f"Failed to complete {withdrawal.id}: {e}", level=messages.ERROR)
        if completed_count > 0:
            self.message_user(request, f"Completed {completed_count} withdrawal requests.", level=messages.SUCCESS)
        else:
            self.message_user(request, "No approved withdrawals to complete.", level=messages.WARNING)

    complete_withdrawals.short_description = "Mark selected approved withdrawals as completed"

admin_site.register(WithdrawalRequest, WithdrawalRequestAdmin)

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_read', 'is_active', 'created_at')
    list_filter = ('title', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at',)
    list_select_related = ('user',)   
admin_site.register(Notification, NotificationAdmin)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
admin_site.register(Category, CategoryAdmin)

class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
admin_site.register(Language, LanguageAdmin)

class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'symbol')
    search_fields = ('code', 'name')
admin_site.register(Currency, CurrencyAdmin)

class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'target_type', 'target_id', 'timestamp')
    list_filter = ('action_type', 'target_type', 'timestamp')
    search_fields = ('user__username', 'target_id', 'description')
    readonly_fields = ('timestamp',)
    list_select_related = ('user',)

admin_site.register(AuditLog, AuditLogAdmin)


