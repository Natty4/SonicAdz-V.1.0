from django.shortcuts import redirect
from django.urls import resolve
from users.models import UserType
    
    
class UserTypeAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.advertiser_paths = ['/advertiser', '/api/advertiser']
        self.creator_paths = ['/main', '/creator', '/api/channels/', '/api/ad-placements', '/api/payments']

    def __call__(self, request):
        user = request.user

        if not user.is_authenticated:
            return self.get_response(request)
        
        if user.is_superuser or user.is_staff:
            return self.get_response(request)

        try:
            resolver_match = resolve(request.path_info)
            app_name = resolver_match.app_name
        except Exception:
            app_name = None

        path = request.path_info

        if user.user_type == UserType.CREATOR:
            if app_name == 'advertiser' or any(path.startswith(p) for p in self.advertiser_paths):
                return redirect('/main/')

        if user.user_type == UserType.ADVERTISER:
            if app_name == 'creator' or any(path.startswith(p) for p in self.creator_paths):
                return redirect('/advertiser/')

        return self.get_response(request)
