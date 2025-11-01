import logging
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.utils.dateparse import parse_datetime

from django.contrib.auth import get_user_model, login
from miniapp.utils import (
    TelegramAuthHelper,
    generate_otp,
    send_otp_via_telegram,
    is_otp_cooldown_active,
    store_otp_in_session,
    is_otp_valid,
    clear_otp_session_data,
    get_client_ip,
    get_user_agent,
    get_device_info,
)
from users.models import TelegramProfile, UserType
from miniapp.models import TelegramVisitorLog
# from django_ratelimit.decorators import ratelimit



logger = logging.getLogger(__name__)

User = get_user_model() 
@csrf_exempt
@require_POST
def process_telegram_auth_view(request):
    try:
        # Get init_data from POST body
        init_data = request.POST.get('init_data')
        if not init_data:
            return redirect('creator:unauthorized') 

        # Validate init data
        if not TelegramAuthHelper.is_valid_telegram_init_data(init_data, settings.BOT_SECRET_TOKEN):
            return redirect('creator:unauthorized') 

        # Extract user data
        user_data = TelegramAuthHelper.extract_telegram_user_data(init_data)
        if not user_data:
            return redirect('creator:unauthorized') 

        tg_id = user_data["id"]
        
        ip = get_client_ip(request)
        device_info = get_device_info(request)

        TelegramVisitorLog.objects.create(
            telegram_id=tg_id,
            username=user_data.get("username"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            is_premium=user_data.get("is_premium", False),
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
        
        # Check user status and redirect appropriately
        profile = TelegramProfile.objects.select_related("user").filter(tg_id=tg_id).first()
        
        if profile:
            user = profile.user
            
            if not user.is_active:
                    return redirect('creator:auth')  
                
            if request.user.is_authenticated and request.user.id == user.id:
                return redirect('creator:main') 
            
            else:
                # Convert PhoneNumber to string before session storage
                phone_number_str = str(user.phone_number)  # Convert here
                
                # Store necessary data in session
                request.session["otp_tg_id"] = tg_id
                request.session["pending_otp_user_id"] = user.id
                request.session["otp_phone_number"] = phone_number_str  # Use string version
                
                # Send OTP immediately
                otp = generate_otp()
                success = send_otp_via_telegram(tg_id, otp)
                
                if success:
                    store_otp_in_session(request.session, otp, user.id)
                    return redirect('creator:otp') 
                else:
                    return redirect('creator:unauthorized') 
        else:
            # Case 3: New user
            request.session["tg_init_data"] = init_data
            request.session["tg_user_data"] = user_data
            return redirect('creator:auth') 
            
    except Exception as e:
        logger.error(f"Error in auth processing: {str(e)}")
        return redirect('creator:unauthorized') 

@csrf_exempt
@require_POST
def telegram_auth_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)

    # Required fields
    required_fields = ['init_data', 'phone_number']
    if any(field not in data for field in required_fields):
        return JsonResponse(
            {"error": f"Missing required fields: {', '.join(required_fields)}"},
            status=400
        )

    return TelegramAuthHelper.process_telegram_auth(
        request,
        data
    )
    
# @login_required
def auth_view(request):
    # Check if user is already logged in and is a creator
    user = request.user

    if user.is_authenticated and user.user_type == UserType.CREATOR and request.session.get("auth_source") == "telegram":
        return redirect('creator:main')
    # Otherwise, render authentication view
    context = {
        'bot': settings.BOT_LINK,
    }
    return render(request, 'creator/auth.html', context)


def otp_view(request):
    # Check if we have the required session data
    if not request.session.get("otp_tg_id") or not request.session.get("pending_otp_user_id"):
        return redirect("creator:landing")
    
    tg_id = request.session.get("otp_tg_id")

    profile = TelegramProfile.objects.select_related("user").filter(tg_id=tg_id).first()
    user_active = profile.user.is_active if profile else False
    if not user_active:
        return redirect("creator:auth")
    # Get phone number for display (last 4 digits)
    phone = request.session.get("otp_phone_number", "")
    display_phone = f"******{phone[-4:]}" if phone else "your phone"
    
    context = {
        'bot': settings.BOT_LINK,
        'display_phone': display_phone,
    }
    return render(request, 'creator/otp.html', context)


def telegram_unauthorized(request):
    error_message = request.GET.get('error', "Unauthorized access.")
    
    context = {
        'bot': settings.BOT_LINK,
        'error': error_message
    }
    return render(request, "creator/unauthorized.html", context)


def request_otp_view(request):
    tg_id = request.session.get("otp_tg_id")

    if not tg_id:
        return redirect("creator:auth")

    profile = TelegramProfile.objects.select_related("user").filter(tg_id=tg_id).first()

    if not profile:
        return redirect("creator:auth")
    
    if profile and not profile.user.is_active:
        return redirect("creator:auth")

    if is_otp_cooldown_active(request.session):
        return JsonResponse({"error": "Please wait before resending."}, status=429)

    otp = generate_otp()
    success = send_otp_via_telegram(tg_id, otp)

    if not success:
        return JsonResponse({"error": "Failed to send OTP via Telegram"}, status=500)

    store_otp_in_session(request.session, otp, profile.user.id)

    return JsonResponse({"success": True})


def verify_otp_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user_input = request.POST.get("otp", "").strip()
    is_valid, error_msg = is_otp_valid(request.session, user_input)

    if not is_valid:
        return JsonResponse({"error": error_msg}, status=403 if "expired" in error_msg else 401)

    user_id = request.session.get("otp_user_id")
    user = User.objects.filter(id=user_id).first()

    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

    login(request, user)
    clear_otp_session_data(request.session)

    return JsonResponse({"success": True, "redirect_url": "/main/"})