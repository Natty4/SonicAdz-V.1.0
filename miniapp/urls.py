from django.urls import path
from miniapp.views.creators import (
    telegram_auth_view, 
    auth_view, 
    process_telegram_auth_view,
    telegram_unauthorized, 
    dashboard_view,
    request_otp_view, 
    verify_otp_view,
    landing_view,
    otp_view,
)
# from creator.bot.views import telegram_webhook

app_name = 'creator'


urlpatterns = [
    path('', landing_view, name='landing'),
    path('auth/', auth_view, name='auth'),
    path('otp/', otp_view, name='otp'),
    path('main/', dashboard_view, name='main'),
    path('process-auth/', process_telegram_auth_view, name='process_telegram_auth'),
    path('unauthorized/', telegram_unauthorized, name='unauthorized'),
    path('api/auth/telegram/', telegram_auth_view, name='api_telegram_auth'),
    path('otp/resend/', request_otp_view, name='otp_resend'),
    path('otp/verify/', verify_otp_view, name='otp_verify'),
    
    # path('telegram/webhook/', telegram_webhook, name='telegram_webhook'),
]
