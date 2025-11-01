import uuid
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import date

from core.models import AdPlacement, AdPerformance
from payments.models import Escrow
from payments.services import EarningService
from core.services.content_delivery_engine import ContentDeliveryService

logger = logging.getLogger(__name__)


class PerformanceLoggingEngine:
    """
    Logs hourly performance snapshots for active AdPlacements by calculating
    deltas from cumulative metrics and processing payments through escrow.
    If budget threshold is exceeded, removes the most expensive placements
    to keep costs within bounds.
    """

    def __init__(self, metrics_source, bot_token=None):
        """
        :param metrics_source: Callable or service that returns latest cumulative
                               performance for a given AdPlacement.
        :param bot_token: Optional Telegram bot token
        """
        self.metrics_source = metrics_source
        self.delivery_service = ContentDeliveryService(bot_token)

    def run(self):
        """
        Main entrypoint — iterate through all active AdPlacements
        and record performance deltas or remove them if over budget.
        """
        logger.info(":- Running PerformanceLoggingEngine...")

        active_placements = AdPlacement.objects.filter(
            is_active=True,
            status__in=['approved', 'completed']
        )

        # Group by campaign
        campaigns = {}
        for placement in active_placements:
            campaign_id = placement.ad.campaign.id
            campaigns.setdefault(campaign_id, []).append(placement)

        for campaign_id, placements in campaigns.items():
            try:
                self._process_campaign_placements(placements)
            except Exception as e:
                logger.error(f"* Failed to process Campaign {campaign_id}: {str(e)}")

    def _process_campaign_placements(self, placements):
        if not placements:
            return

        campaign = placements[0].ad.campaign
        total_budget = campaign.initial_budget or Decimal('0.00')
        total_spent = campaign.total_spent or Decimal('0.00')
        remaining_budget = total_budget - total_spent

        logger.info(f": Campaign {campaign.id} | Remaining budget: {remaining_budget}")

        # Prepare placement deltas
        placement_deltas = []
        for placement in placements:
            current_snapshot = self.metrics_source(placement)
            if not current_snapshot:
                logger.warning(f": No data returned for placement {placement.id}")
                continue

            prev = self._get_previous_metrics(placement)
            channel_cpm = float(placement.channel.min_cpm or 0)
            delta = self._calculate_delta(prev, current_snapshot, cpm=channel_cpm)

            if delta['cost'] <= 0:
                logger.info(f": No performance delta for placement {placement.id}, skipping.")
                continue

            placement_deltas.append({
                'placement': placement,
                'delta': delta,
                'cost': delta['cost']
            })

        if not placement_deltas:
            logger.info(": No valid performance deltas to process.")
            return

        # Estimate total cost
        estimated_total_cost = sum(item['cost'] for item in placement_deltas)
        threshold = remaining_budget - estimated_total_cost

        logger.info(f": Estimated total cost: {estimated_total_cost} | Threshold: {threshold}")

        if threshold >= 0:
            for item in placement_deltas:
                self._log_performance(item['placement'], item['delta'])
            return

        # Budget risk — remove highest-cost placements using greedy approach
        placement_deltas.sort(key=lambda x: x['cost'], reverse=True)

        selected = []
        running_cost = Decimal('0.00')
        for item in placement_deltas:
            if running_cost + item['cost'] <= remaining_budget:
                selected.append(item)
                running_cost += item['cost']

        removed = [item for item in placement_deltas if item not in selected]

        logger.warning(f": Removing {len(removed)} placements to stay within budget.")

        # Remove & mark placements
        for item in removed:
            self._deactivate_and_remove_post(item['placement'])

        if not selected:
            campaign.status = 'stopped'
            campaign.save(update_fields=['status'])
            logger.warning(f": All placements removed for campaign {campaign.id} — marking campaign stopped.")
            return

        # Log for kept placements
        for item in selected:
            self._log_performance(item['placement'], item['delta'])

    def _get_previous_metrics(self, placement):
        """Fetch previous cumulative metrics for a placement."""
        prev_performance = {
            'impressions': 0,
            'clicks': 0,
            'conversions': 0,
            'reposts': 0,
            'total_reactions': 0,
            'total_replies': 0,
            'views': 0,
            'forwards': 0,
        }

        past_perfs = AdPerformance.objects.filter(ad_placement=placement)
        for perf in past_perfs:
            prev_performance['impressions'] += perf.impressions
            prev_performance['clicks'] += perf.clicks
            prev_performance['conversions'] += perf.conversions
            prev_performance['reposts'] += perf.reposts
            prev_performance['total_reactions'] += perf.total_reactions
            prev_performance['total_replies'] += perf.total_replies
            prev_performance['views'] += perf.views
            prev_performance['forwards'] += perf.forwards

        return prev_performance

    def _deactivate_and_remove_post(self, placement):
        """Remove post from channel and mark placement as completed, with admin notification."""
        try:
            result = self.delivery_service.delete_from_channel(placement)

            if result.get("success"):
                logger.info(f": Deleted post for placement {placement.id}")
                reason = f"Deleted due to budget constraints for Campaign {placement.ad.campaign.id}."
            else:
                logger.warning(f": Failed to delete post for placement {placement.id}: {result.get('error')}")
                reason = f"Attempted deletion due to budget constraint failed: {result.get('error')}"

            # Notify admin about the reason for removal
            self.delivery_service.bot_util.notify_admin_failure(
                placement,
                reason
            )

            # Update placement status regardless of Telegram result
            placement.status = 'completed'
            placement.save(update_fields=['status'])

        except Exception as e:
            logger.error(f"* Error deactivating placement {placement.id}: {str(e)}")
            self.delivery_service.bot_util.notify_admin_failure(
                placement,
                f"Exception while deleting post: {str(e)}"
            )

    def _log_performance(self, placement, delta):
        """Log performance and deduct earnings."""
        today = date.today()
        advertiser = placement.ad.campaign.advertiser
        creator = placement.channel.owner
        campaign = placement.ad.campaign

        past_perfs = AdPerformance.objects.filter(ad_placement=placement)
        last_perf = past_perfs.order_by('-timestamp').first()
        time_diff = timezone.now() - last_perf.timestamp if last_perf else None

        with transaction.atomic():
            performance = AdPerformance.objects.create(
                ad_placement=placement,
                date=today,
                impressions=delta['impressions'],
                clicks=delta['clicks'],
                conversions=delta['conversions'],
                reposts=delta['reposts'],
                cost=delta['cost'],
                total_reactions=delta['total_reactions'],
                total_replies=delta['total_replies'],
                views=delta['views'],
                forwards=delta['forwards'],
                time_delta=time_diff,
                is_deducted=False
            )

            escrow = Escrow.objects.filter(
                advertiser=advertiser,
                assigned_creators=creator,
                campaign=campaign,
                status='pending'
            ).first()

            if not escrow:
                raise ValueError("* No valid escrow found for advertiser and creator.")

            unique_suffix = uuid.uuid4().hex[:6].upper()
            reference = f"ADP-{placement.id}-PERF-{performance.timestamp:%Y%m%d%H%M}-{unique_suffix}"

            EarningService.record_earning(
                escrow_id=escrow.id,
                creator=creator,
                amount=delta['cost'],
                reference=reference
            )

            performance.is_deducted = True
            performance.save()

            campaign.total_spent = (campaign.total_spent or Decimal('0.00')) + delta['cost']
            campaign.save(update_fields=['total_spent'])

            logger.info(f": Logged AdPlacement {placement.id} | Δ Cost: {delta['cost']}")

    def _calculate_delta(self, prev_performance, current_snapshot, cpm):
        """
        Calculates delta from total previously logged metrics vs current snapshot.
        Returns a dict of deltas and the cost.
        """
        impression_delta = current_snapshot['impressions'] - prev_performance['impressions']
        cost = Decimal(impression_delta * cpm / 1000) if cpm else Decimal('0.00')

        return {
            'impressions': impression_delta,
            'clicks': current_snapshot['clicks'] - prev_performance['clicks'],
            'conversions': current_snapshot['conversions'] - prev_performance['conversions'],
            'reposts': current_snapshot['reposts'] - prev_performance['reposts'],
            'cost': cost,
            'total_reactions': current_snapshot['total_reactions'] - prev_performance['total_reactions'],
            'total_replies': current_snapshot['total_replies'] - prev_performance['total_replies'],
            'views': current_snapshot['views'] - prev_performance['views'],
            'forwards': current_snapshot['forwards'] - prev_performance['forwards'],
        }
