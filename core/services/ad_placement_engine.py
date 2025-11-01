import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from core.models import AdPlacement, PlacementMatchLog, Campaign
from creators.models import CreatorReputation

logger = logging.getLogger(__name__)

class AdPlacementEngine:
    FALLBACK_ENGAGEMENT = 0.15  # 15% engagement if no data
    MINIMUM_FUND = 100  # ETB
    OBJECTIVE_CONFIG = {
        'brand_awareness': {
            'max_channels': 20,
            'weights': {
                'match_score': 0.4,
                'subscribers': 0.4,
                'fraud': 0.1,
                'engagement_rate': 0.1,
            }
        },
        'engagement': {
            'max_channels': 5,
            'weights': {
                'engagement_rate': 0.5,
                'rating': 0.3,
                'match_score': 0.2,
            }
        },
        'conversion': {
            'max_channels': 3,
            'weights': {
                'fraud': 0.4,
                'rating': 0.4,
                'match_score': 0.2,
            }
        },
        'traffic': {
            'max_channels': 10,
            'weights': {
                'subscribers': 0.3,
                'match_score': 0.3,
                'engagement_rate': 0.2,
                'rating': 0.2,
            }
        }
    }

    def __init__(self, campaign: Campaign, matched_channels_with_score: list):
        self.campaign = campaign
        self.matched_channels = matched_channels_with_score
        self.config = self.OBJECTIVE_CONFIG.get(campaign.objective, self.OBJECTIVE_CONFIG['brand_awareness'])

    def _estimate_cost(self, channel, engagement_rate: float) -> Decimal:
        expected_views = max(channel.subscribers, 1) * engagement_rate
        estimated_cost = Decimal((expected_views / 1000) * float(max(self.campaign.cpm, 0.01)))
        return estimated_cost

    def _score_channel(self, channel, match_score: float) -> tuple[float, float]:
        try:
            reputation = channel.reputation
        except CreatorReputation.DoesNotExist:
            reputation = None

        rating = reputation.rating if reputation else 5.0
        fraud = reputation.fraud_score if reputation else 0.0
        engagement_rate = getattr(reputation, 'avg_engagement_rate', self.FALLBACK_ENGAGEMENT)
        subscribers = channel.subscribers

        weights = self.config['weights']

        score = (
            weights.get('match_score', 0) * match_score +
            weights.get('subscribers', 0) * (subscribers / 1_000_000) +
            weights.get('rating', 0) * (rating / 5.0) +
            weights.get('fraud', 0) * (1 - fraud) +
            weights.get('engagement_rate', 0) * engagement_rate
        )

        if channel.auto_publish:
            score += 0.05  # Slight boost for automation

        score = float(f"{score:.2f}")
        return score, engagement_rate

    def assign_placements(self) -> list:
        assigned = []
        active_ads = self.campaign.ads.filter(is_active=True)

        if not active_ads.exists():
            logger.warning(f"No active ads for campaign {self.campaign.id}")
            return assigned

        with transaction.atomic():
            for ad in active_ads:
                for channel, match_score, estimated_cost in self.matched_channels:
                    try:
                        placement, created = AdPlacement.objects.get_or_create(
                            ad=ad,
                            channel=channel,
                            defaults={
                                'status': 'draft',
                                'preference_score': match_score,
                                'winning_bid_price': channel.min_cpm
                            }
                        )

                        if placement.status not in ['draft', 'completed']:
                            continue  # Skip non-draft reassignments

                        assigned.append((channel.title, match_score))

                        if created:
                            _, engagement_rate = self._score_channel(channel, match_score)
                            estimated_cost = self._estimate_cost(channel, engagement_rate)

                            PlacementMatchLog.objects.create(
                                campaign=self.campaign,
                                ad_placement=placement,
                                reason=(
                                    f"[Initial Match] "
                                    f"Channel: {channel.title} | "
                                    f"Score: {match_score:.2f} | "
                                    f"Estimated Cost: {estimated_cost:.2f} ETB | "
                                    f"Campaign Budget: {self.campaign.initial_budget:.2f} ETB | "
                                    f"Subscribers: {channel.subscribers} | "
                                    f"Min CPM: {channel.min_cpm} | "
                                    f"Objective: {self.campaign.objective}"
                                ),
                                estimated_cost=estimated_cost
                            )
                            logger.info(f"Created placement for campaign {self.campaign.id}, channel {channel.title}")
                        else:
                            logger.info(f"Found existing placement (draft) for campaign {self.campaign.id}, channel {channel.title}")

                    except Exception as e:
                        logger.error(f"Error during assignment: {self.campaign.id}, channel {channel.title} — {str(e)}")

        if not assigned:
            logger.error(f"No placements assigned for campaign {self.campaign.id}. Channels tried: {[c[0].title for c in self.matched_channels]}")
        return assigned

    def activate_placements(self) -> list:
        activated = []
        skipped_due_to_budget = []

        if not self.campaign.ads.filter(is_active=True).exists():
            logger.warning(f"No active ads for campaign {self.campaign.id}")
            return activated

        if self.campaign.end_date and self.campaign.end_date < timezone.now().date():
            self.campaign.status = 'completed'
            self.campaign.save()
            logger.warning(f"Campaign {self.campaign.id} has expired")
            return activated

        if self.campaign.start_date and self.campaign.start_date > timezone.now().date():
            self.campaign.status = 'scheduled'
            self.campaign.save()
            logger.warning(f"Campaign {self.campaign.id} is not yet active")
            return activated

        escrows = self.campaign.escrows.filter(status='pending')
        if not escrows.exists():
            logger.warning(f"No pending escrows for campaign {self.campaign.id}")
            return activated

        budget_remaining = sum(e.remaining_amount for e in escrows)
        if budget_remaining <= self.MINIMUM_FUND:
            logger.warning(f"Insufficient funds: {budget_remaining} ETB remaining in campaign {self.campaign.id}")
            return activated

        draft_placements = AdPlacement.objects.filter(ad__campaign=self.campaign, status__in=['draft', 'completed'])
        scored_channels = []

        for placement in draft_placements:
            channel = placement.channel
            if not (channel.is_active and channel.status == 'verified'):
                continue
            if channel.min_cpm > self.campaign.cpm:
                continue

            score, engagement = self._score_channel(channel, placement.preference_score)
            cost = self._estimate_cost(channel, engagement)
            scored_channels.append((channel, score, engagement, cost))

        scored_channels.sort(key=lambda x: x[1], reverse=True)
        max_channels = self.config['max_channels']
        escrow = escrows.first()

        with transaction.atomic():
            for ad in self.campaign.ads.filter(is_active=True):
                count = 0
                for channel, score, engagement, cost in scored_channels:
                    if count >= max_channels:
                        break

                    if cost > budget_remaining:
                        skipped_due_to_budget.append(channel.title)
                        continue

                    try:
                        placement, created = AdPlacement.objects.get_or_create(
                            ad=ad,
                            channel=channel,
                            defaults={
                                'preference_score': score,
                                'status': 'approved' if channel.auto_publish else 'pending',
                                'winning_bid_price': channel.min_cpm
                            }
                        )
                        if not created and placement.status in ['approved', 'expired']: # 'completed'
                            continue

                        placement.status = 'approved' if channel.auto_publish else 'pending'
                        placement.preference_score = score
                        placement.max_reposts = channel.repost_preference_frequency
                        placement.winning_bid_price = channel.min_cpm
                        placement.save()

                        if not escrow.assigned_creators.filter(id=channel.owner.id).exists():
                            escrow.assigned_creators.add(channel.owner)

                        budget_remaining -= cost
                        activated.append((channel.title, float(cost)))
                        count += 1

                        PlacementMatchLog.objects.create(
                            campaign=self.campaign,
                            ad_placement=placement,
                            reason=(
                                f"[Activated] "
                                f"Channel: {channel.title} | "
                                f"Score: {score:.2f} | "
                                f"Engagement Rate: {engagement:.2%} | "
                                f"Estimated Cost: {cost:.2f} ETB | "
                                f"Remaining Budget: {budget_remaining + cost:.2f} ETB → {budget_remaining:.2f} ETB | "
                                f"Subscribers: {channel.subscribers} | "
                                f"Min CPM: {channel.min_cpm} | "
                                f"Objective: {self.campaign.objective}"
                            ),
                            estimated_cost=cost
                        )
                        logger.info(f"Activated placement {placement.id} for campaign {self.campaign.id}, channel {channel.title}, cost={cost}")

                    except Exception as e:
                        logger.error(f"Failed activation: Campaign {self.campaign.id}, Channel {channel.title} — {str(e)}")

        if skipped_due_to_budget:
            logger.warning(f"Skipped due to insufficient budget: {skipped_due_to_budget}")

        return activated
