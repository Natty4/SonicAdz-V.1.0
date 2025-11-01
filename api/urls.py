from django.urls import path
from api.views.creators import (
    DashboardAPIView,
    ChannelsAPIView,
    ChannelDetailAPIView,
    AdsAPIView,
    AdDetailAPIView,
    TransactionsAPIView,
    PaymentListCreateAPIView,
    PaymentDetailAPIView,
    PaymentMethodsChoice,
    WithdrawalAPIView,
    ActiveCategoryListAPIView,
    LanguageListAPIView,
    ConnectChannelAPIView,
    VerifyChannelAPIView,
    ApproveAdPlacement,
    RejectAdPlacement,
    ChannelMLScoreBulkUpdateAPIView,
    VerifiedChannelListAPIView,
    
)
from api.views.campaigns import (
    CampaignViewSet,
    CampaignSubmitAPIView,
    CampaignPauseAPIView,
    CampaignResumeAPIView,
    CampaignStopAPIView,
    BalanceDepositRequestAPIView,
    BalanceDepositConfirmAPIView,
    BalanceDepositStatusAPIView,
    BalanceSummaryAPIView,
    PerformanceListAPIView,
    PerformanceSummaryAPIView,
    PerformanceExportAPIView,
)
from api.views.users import (
    UserProfileAPIView,
)
from api.views.performance import ( 
    ActiveAdPlacementsView, RecordAdPerformanceView
)
from api.views.notifications import (
    NotificationListCreateView,
    NotificationDetailView,
    NotificationMarkReadView,
    NotificationMarkUnreadView,
    NotificationMarkAllReadView,
    NotificationUnreadCountView
)

from django.urls import path, include
from rest_framework.routers import DefaultRouter


urlpatterns = [
       
    # Dashboard
    path('dashboard/', DashboardAPIView.as_view(), name='api_dashboard'),
    
    # Channels
    path('channels/', ChannelsAPIView.as_view(), name='api_channels'),
    path('channels/<uuid:id>/', ChannelDetailAPIView.as_view(), name='api_channel_detail'),
    
    # Ads
    path('ad-placements/', AdsAPIView.as_view(), name='api_ads'),
    path('ads/<uuid:ad_id>/', AdDetailAPIView.as_view(), name='api_ad_detail'),
    path('ad-placements/<uuid:pk>/approve/', ApproveAdPlacement.as_view(), name='api_approve_adplacement'),
    path('ad-placements/<uuid:pk>/reject/', RejectAdPlacement.as_view(), name='api_reject_adplacement'),
    
    # Payments
    path('transactions/', TransactionsAPIView.as_view(), name='api_transactions'),
    
    
    path('payments/', PaymentListCreateAPIView.as_view(), name='api_payments'),
    path('payment-methods/<uuid:method_id>/', PaymentDetailAPIView.as_view(), name='payment-method-detail'),
    path('payment-method-choice/', PaymentMethodsChoice.as_view(), name='api_payment_choices'),
    path('payments/deposit/request/', BalanceDepositRequestAPIView.as_view(), name='api_balance_deposit_request'),
    path('payments/deposit/confirm/', BalanceDepositConfirmAPIView.as_view(), name='api_balance_deposit_confirm'),
    path('payments/deposit/status/<str:tx_ref>/', BalanceDepositStatusAPIView.as_view(), name='api_balance_deposit_status'),

    path('withdrawal/request/', WithdrawalAPIView.as_view(), name='api_withdraw'),
    
    # Channel management
    path('categories/', ActiveCategoryListAPIView.as_view(), name='api_categories'),
    path('languages/', LanguageListAPIView.as_view(), name='api_languages'),
    path('channels/connect/', ConnectChannelAPIView.as_view(), name='api_connect_channel'),
    path('channels/verify/', VerifyChannelAPIView.as_view(), name='api_verify_channel'),
    path('channels/verify/<uuid:channel_id>/', VerifyChannelAPIView.as_view(), name='api_verify_channel_with_id'),
    
    
    path('settings/user/', UserProfileAPIView.as_view(), name='api_user_profile'),
    
    
    # Advertiser Endpoints (New)
    path('advertiser/campaigns/<uuid:pk>/submit/', CampaignSubmitAPIView.as_view(), name='api_campaign_submit'),
    path('advertiser/campaigns/<uuid:pk>/pause/', CampaignPauseAPIView.as_view(), name='api_campaign_pause'),
    path('advertiser/campaigns/<uuid:pk>/resume/', CampaignResumeAPIView.as_view(), name='api_campaign_resume'),
    path('advertiser/campaigns/<uuid:pk>/stop/', CampaignStopAPIView.as_view(), name='api_campaign_stop'),
    path('advertiser/balance/summary/', BalanceSummaryAPIView.as_view(), name='api_balance_summary'),
    path('advertiser/performance/', PerformanceListAPIView.as_view(), name='api_performance'),
    path('advertiser/performance/summary/', PerformanceSummaryAPIView.as_view(), name='api_performance_summary'),
    path('advertiser/performance/export/', PerformanceExportAPIView.as_view(), name='api_performance_export'),
    
    
    
    
    path('notifications/', NotificationListCreateView.as_view(), name='notification-list-create'),
    path('notifications/<uuid:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/<uuid:pk>/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('notifications/<uuid:pk>/mark-unread/', NotificationMarkUnreadView.as_view(), name='notification-mark-unread'),
    path('notifications/mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    
    
    
    #helper endpoint protected with header
    path('active-ad-placements/', ActiveAdPlacementsView.as_view(), name='active_ad_placements'),
    path('performance-report/', RecordAdPerformanceView.as_view(), name='record_ad_performance'),
    
    
    path('update-ml-scores/', ChannelMLScoreBulkUpdateAPIView.as_view(), name='update-ml-scores'),
    path('verified-channels/', VerifiedChannelListAPIView.as_view(), name='verified-channels'),
]




router = DefaultRouter()
router.register(r'campaigns', CampaignViewSet, basename='campaign')

urlpatterns += [
    path('advertiser/', include(router.urls)),
]