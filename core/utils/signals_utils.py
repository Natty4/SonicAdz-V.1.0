from django.utils import timezone
from core.services.ad_placement_engine import AdPlacementEngine
from core.models import AdPlacement, AdPlacementStatus
from core.services.content_delivery_engine import ContentDeliveryService
from threading import local
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
_thread_locals = local()

def process_campaign_activation(campaign):
    if not campaign.ads.filter(is_active=True).exists():
        logger.warning(f"Campaign '{campaign.name}' has no active ads, skipping activation.")
        return

    if campaign.end_date and campaign.end_date < timezone.now().date():
        logger.warning(f"Campaign '{campaign.name}' has expired, marking as completed.")
        campaign.status = 'completed'
        campaign.save(update_fields=['status'])
        return

    if campaign.start_date and campaign.start_date > timezone.now().date():
        logger.warning(f"Campaign '{campaign.name}' is scheduled for a future date.")
        campaign.status = 'scheduled'
        campaign.save(update_fields=['status'])
        return

    setattr(_thread_locals, 'campaign_approval', True)
    try:
        engine = AdPlacementEngine(campaign, [])
        activated = engine.activate_placements()
        logger.info(f"Activated placements for campaign {campaign.id}: {activated}")
        delivery_service = ContentDeliveryService(settings.BOT_SECRET_TOKEN)

        for channel_title, cost in activated:
            try:
                placement = AdPlacement.objects.get(ad__campaign=campaign, channel__title=channel_title)
                if placement.status == AdPlacementStatus.APPROVED:
                    setattr(_thread_locals, 'posting_in_progress', True)
                    try:
                        original_status = placement.status or AdPlacementStatus.PENDING
                        result = delivery_service.post_to_channel(placement)
                        if not result['success']:
                            placement.status = original_status
                            placement.save(update_fields=['status'])
                            logger.error(f"Failed to post to Telegram for placement {placement.id}: {result['error']}")
                        else:
                            campaign.start_date = timezone.now().date()
                            campaign.save(update_fields=['start_date'])
                    finally:
                        setattr(_thread_locals, 'posting_in_progress', False)
            except AdPlacement.DoesNotExist:
                logger.error(f"Placement not found for campaign {campaign.id}, channel {channel_title}")
            except Exception as e:
                logger.error(f"Failed to process placement for campaign {campaign.id}, channel {channel_title}: {str(e)}")
    finally:
        setattr(_thread_locals, 'campaign_approval', False)

def process_placement_approval(placement):
    if getattr(_thread_locals, 'campaign_approval', False):
        logger.info(f"Skipping Telegram post for placement {placement.id} as it was handled by campaign approval")
        return

    if getattr(_thread_locals, 'posting_in_progress', False):
        logger.info(f"Skipping Telegram post for placement {placement.id} due to ongoing posting")
        return

    if placement.ad.campaign.status != 'active':
        logger.warning(f"Cannot post placement '{placement.id}' as campaign is not active.")
        return

    delivery_service = ContentDeliveryService(settings.BOT_SECRET_TOKEN)
    original_status = placement.status or AdPlacementStatus.PENDING
    setattr(_thread_locals, 'posting_in_progress', True)
    try:
        result = delivery_service.post_to_channel(placement)
        if not result['success']:
            placement.status = AdPlacementStatus.PENDING
            placement.save(update_fields=['status'])
            logger.error(f"Failed to post to Telegram for placement {placement.id}: {result['error']}")
    except Exception as e:
        placement.status = original_status
        placement.save(update_fields=['status'])
        logger.error(f"Failed to post to Telegram for placement {placement.id}: {str(e)}")
    finally:
        setattr(_thread_locals, 'posting_in_progress', False)















































# from django.utils import timezone
# from core.services.ad_placement_engine import AdPlacementEngine
# from core.models import AdPlacement
# from core.utils.bot_utils import TelegramPostingUtil
# from threading import local
# from django.conf import settings
# import logging

# logger = logging.getLogger(__name__)
# _thread_locals = local()

# def process_campaign_activation(campaign):
#     if not campaign.ads.filter(is_active=True).exists():
#         logger.warning(f"Campaign '{campaign.name}' has no active ads, skipping activation.")
#         return

#     if campaign.end_date and campaign.end_date < timezone.now().date():
#         logger.warning(f"Campaign '{campaign.name}' has expired, marking as completed.")
#         campaign.status = 'completed'
#         campaign.save(update_fields=['status'])
#         return

#     if campaign.start_date and campaign.start_date > timezone.now().date():
#         logger.warning(f"Campaign '{campaign.name}' is scheduled for a future date.")
#         campaign.status = 'scheduled'
#         campaign.save(update_fields=['status'])
#         return

#     setattr(_thread_locals, 'campaign_approval', True)
#     try:
#         engine = AdPlacementEngine(campaign, [])
#         activated = engine.activate_placements()
#         logger.info(f"Activated placements for campaign {campaign.id}: {activated}")
#         bot_util = TelegramPostingUtil(settings.BOT_SECRET_TOKEN)

#         for channel_title, cost in activated:
#             try:
#                 placement = AdPlacement.objects.get(ad__campaign=campaign, channel__title=channel_title)
#                 if placement.status == 'approved':
#                     # Set flag to prevent signal loop
#                     setattr(_thread_locals, 'posting_in_progress', True)
#                     try:
#                         original_status = placement.status or 'pending'
#                         result = bot_util.send_message_to_channel(
#                             channel_id=placement.channel.channel_id,
#                             text_content=placement.ad.text_content,
#                             headline=placement.ad.headline,
#                             image_url=placement.ad.img_url,
#                             social_links=placement.ad.social_links,
#                             brand_name=placement.ad.brand_name or "Visit",
#                             sonic=None
#                         )
#                         if result['success']:
#                             placement.content_platform_id = str(result['link'])
#                             placement.status = 'running'
#                             placement.save(update_fields=['content_platform_id', 'status'])
#                             campaign.start_date = timezone.now().date()
#                             campaign.save(update_fields=['start_date'])
#                             logger.info(f"Posted to Telegram for placement {placement.id}, channel")
#                         else:
#                             placement.status = original_status
#                             placement.save(update_fields=['status'])
#                             logger.error(f"Failed to post to Telegram for placement {placement.id}: {result['error']}. Reverted status to {original_status}")
#                             bot_util.notify_admin_failure(placement, result['error'])
#                     finally:
#                         setattr(_thread_locals, 'posting_in_progress', False)
#             except AdPlacement.DoesNotExist:
#                 logger.error(f"Placement not found for campaign {campaign.id}, channel {channel_title}")
#             except Exception as e:
#                 logger.error(f"Failed to process placement {placement.id}: {str(e)}")
#     finally:
#         setattr(_thread_locals, 'campaign_approval', False)

# def process_placement_approval(placement):
#     if getattr(_thread_locals, 'campaign_approval', False):
#         logger.info(f"Skipping Telegram post for placement {placement.id} as it was handled by campaign approval")
#         return

#     if getattr(_thread_locals, 'posting_in_progress', False):
#         logger.info(f"Skipping Telegram post for placement {placement.id} due to ongoing posting")
#         return

#     if placement.ad.campaign.status != 'active':
#         logger.warning(f"Cannot post placement '{placement.id}' as campaign is not active.")
#         return

#     bot_util = TelegramPostingUtil(settings.BOT_SECRET_TOKEN)
#     original_status = placement.status or 'pending'
#     setattr(_thread_locals, 'posting_in_progress', True)
#     try:
#         result = bot_util.send_message_to_channel(
#             channel_id=placement.channel.channel_id,
#             text_content=placement.ad.text_content,
#             headline=placement.ad.headline,
#             image_url=placement.ad.img_url,
#             social_links=placement.ad.social_links,
#             brand_name=placement.ad.brand_name or "Visit",
#             sonic=None
#         )
#         if result['success']:
#             placement.content_platform_id = str(result['link'])
#             placement.save(update_fields=['content_platform_id'])
#             logger.info(f"Posted to Telegram for placement {placement.id}, channel")
#         else:
#             placement.status = 'pending'
#             placement.save(update_fields=['status'])
#             logger.error(f"Failed to post to Telegram for placement {placement.id}: {result['error']}. Reverted status to {original_status}")
#             bot_util.notify_admin_failure(placement, result['error'])
#     except Exception as e:
#         placement.status = original_status
#         placement.save(update_fields=['status'])
#         logger.error(f"Failed to post to Telegram for placement {placement.id}: {str(e)}. Reverted status to {original_status}")
#         bot_util.notify_admin_failure(placement, str(e))
#     finally:
#         setattr(_thread_locals, 'posting_in_progress', False)