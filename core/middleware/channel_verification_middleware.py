from django.utils import timezone
from django.utils.timezone import timedelta
from django.utils.dateparse import parse_datetime
from django.utils.deprecation import MiddlewareMixin
from users.models import UserType
from creators.models import CreatorChannel
from core.services.channel_verification_service import verify_creator_channel


class ChannelVerificationMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user

        if not user.is_authenticated or user.user_type != UserType.CREATOR:
            return None

        last_checked = request.session.get("channel_verification_last_checked")
        if last_checked and timezone.now() - parse_datetime(last_checked) < timedelta(hours=3):
            return None  # Skip

        request.session["channel_verification_last_checked"] = timezone.now().isoformat()

        if request.path not in ["/main/", "/channels/"]:
            return None

        creator_channels = CreatorChannel.objects.filter(owner=user, is_active=True, status__in=["verified"])
        for channel in creator_channels:
            verify_creator_channel(channel) 

        return None
