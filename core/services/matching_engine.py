from django.db.models import Q
from math import log10

from core.models import Campaign
from creators.models import CreatorChannel, CreatorReputation

class CampaignChannelMatcher:

    def __init__(self, campaign: Campaign):
        self.campaign = campaign
        self.categories = set(campaign.targeting_categories.values_list('id', flat=True))
        self.languages = set(campaign.targeting_languages.values_list('id', flat=True))
        self.regions = set(campaign.targeting_regions.get('countries', []))
        self.campaign_cpm = float(campaign.cpm)
        self.budget = float(campaign.initial_budget)

    def get_eligible_channels(self):
        return CreatorChannel.objects.filter(
            is_active=True,
            status='verified',
            min_cpm__lte=self.campaign_cpm,
            # region__in=self.regions,
            language__in=self.languages,
            category__in=self.categories
        ).distinct()

    def estimate_channel_cost(self, channel: CreatorChannel) -> float:
        try:
            rep = channel.reputation
            engagement_rate = rep.avg_engagement_rate or 0.15  # Default 15% if missing
        except CreatorReputation.DoesNotExist:
            engagement_rate = 0.15

        subscribers = channel.subscribers or 0
        estimated_views = subscribers * engagement_rate
        estimated_cost = (estimated_views / 1000) * float(channel.min_cpm)

        return round(estimated_cost, 2)

    def score_channel(self, channel: CreatorChannel) -> float:
        score = 0.0

        # Category match
        channel_categories = set(channel.category.values_list('id', flat=True))
        category_overlap = len(channel_categories & self.categories)
        category_score = (category_overlap / len(self.categories)) * 25 if self.categories else 0
        score += category_score

        # Language match
        channel_langs = set(channel.language.values_list('id', flat=True))
        lang_overlap = len(channel_langs & self.languages)
        lang_score = (lang_overlap / len(self.languages)) * 10 if self.languages else 0
        score += lang_score

        # Region match
        region_score = 10.0 if channel.region in self.regions else 0
        score += region_score

        # CPM compatibility
        cpm_score = 15.0 if self.campaign_cpm >= float(channel.min_cpm) else 0
        score += cpm_score

        # Estimated budget feasibility
        estimated_cost = self.estimate_channel_cost(channel)
        budget_score = 10.0 if self.budget >= estimated_cost else 0
        score += budget_score

        # Reputation score
        try:
            rep = channel.reputation
            rep_score = max(0, (rep.rating - rep.fraud_score)) / 5 * 20
        except CreatorReputation.DoesNotExist:
            rep_score = 10.0  # default
        score += rep_score

        # Subscriber normalization
        subs = channel.subscribers
        subs_score = min(log10(subs + 1), 6) / 6 * 10
        score += subs_score

        return round(score, 2)

    def get_ranked_channels(self, top_n=10):
        channels = self.get_eligible_channels()
        ranked = []

        for channel in channels:
            score = self.score_channel(channel)
            estimated_cost = self.estimate_channel_cost(channel)
            ranked.append((channel, score, estimated_cost))

        # Sort by score descending
        ranked.sort(key=lambda x: x[1], reverse=True)

        # Budget filtering
        selected_channels = []
        total_spent = 0.0

        for channel, score, estimated_cost in ranked:
            if total_spent + estimated_cost <= self.budget:
                selected_channels.append((channel, score, estimated_cost))
                total_spent += estimated_cost
                if len(selected_channels) >= top_n:
                    break
            else:
                continue

        return selected_channels