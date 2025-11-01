from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.models import AdPlacement
from decimal import Decimal
from core.services.ad_performance_engine import PerformanceLoggingEngine

TRUSTED_DISPATCHER_HEADER = "X-Dispatched-By"
TRUSTED_DISPATCHER_VALUE = "local-scraper" 

import logging
logger = logging.getLogger(__name__)

class ActiveAdPlacementsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if request.headers.get(TRUSTED_DISPATCHER_HEADER) != TRUSTED_DISPATCHER_VALUE:
            return Response(
                {"error": "Unauthorized"},
                status=status.HTTP_403_FORBIDDEN
            )

        placements = AdPlacement.objects.filter(
            is_active=True,
            status__in=["approved", "running", "completed"],
            content_platform_id__isnull=False
        )

        data = []
        for p in placements:
            data.append({
                "id": str(p.id),
                "content_platform_id": p.content_platform_id,
                "ad_headline": p.ad.headline,
                "channel_username": p.channel.channel_link.strip('@'),
            })
            

        return Response(data, status=status.HTTP_200_OK)


class RecordAdPerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.headers.get(TRUSTED_DISPATCHER_HEADER) != TRUSTED_DISPATCHER_VALUE:
            return Response(
                {"error": "Unauthorized"},
                status=status.HTTP_403_FORBIDDEN
            )

        payload = request.data
        
        logger.info("[✓] Received performance report")
      
        
        try:
            placement = AdPlacement.objects.get(id=payload.get("placement_id"))
        except AdPlacement.DoesNotExist:
            return Response({"error": "Placement not found"}, status=status.HTTP_404_NOT_FOUND)

        snapshot = {
            'impressions': int(payload.get('impressions', 0)),
            'clicks': int(payload.get('clicks', 0)),
            'conversions': int(payload.get('conversions', 0)),
            'reposts': int(payload.get('reposts', 0)),
            'total_reactions': int(payload.get('total_reactions', 0)),
            'total_replies': int(payload.get('total_replies', 0)),
            'views': int(payload.get('views', 0)),
            'forwards': int(payload.get('forwards', 0)),
        }

        try:
            engine = PerformanceLoggingEngine(
                    metrics_source=lambda _: snapshot,
                    bot_token=settings.BOT_SECRET_TOKEN
                )
            engine._process_campaign_placements([placement])

            logger.info(f"[✓] Performance processed for placement {placement.id}")
            return Response({"status": "Recorded"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception(f"[!] Failed to process performance for placement {placement.id}: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)