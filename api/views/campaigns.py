import logging
import uuid
import requests
import re
import json
import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, F, Value, FloatField, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from django.db.models.expressions import ExpressionWrapper
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import ValidationError
from requests_toolbelt.multipart.encoder import MultipartEncoder
from core.models import Campaign, Ad, AdStatus, AdPerformance
from core.services.matching_engine import CampaignChannelMatcher
from core.services.ad_placement_engine import AdPlacementEngine
from payments.services.payment_service import WalletService, EscrowService
from payments.services.balance_service import BalanceService
from api.serializers.campaigns import CampaignSerializer, PerformanceSerializer
from api.serializers.payments import TransactionSerializer
from api.permissions.campaigns import IsAdvertiser, IsOwnerOfCampaignOrAd







User = get_user_model()
logger = logging.getLogger(__name__)

# Advertiser Views

class CampaignViewSet(viewsets.ModelViewSet):
    """
    Manages Campaign metadata and the single active Ad content via a unified endpoint.
    """
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdvertiser, IsOwnerOfCampaignOrAd] 

    def get_queryset(self):
        # Filter campaigns to only show the logged-in advertiser's campaigns
        if self.request.user.is_authenticated:
            # Prefetch the ads to avoid N+1 queries during serialization
            return self.queryset.filter(advertiser=self.request.user, is_active=True).prefetch_related('ads')
        return self.queryset.none()
    
    def perform_create(self, serializer):
        # Set the advertiser automatically before calling serializer.create()
        # The atomic creation of Campaign and Ad happens inside the serializer.
        serializer.save(advertiser=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        """
        Ensures PATCH requests correctly trigger the full update logic, 
        including the status-based validation in the serializer.
        """
        return super().partial_update(request, *args, **kwargs)


class CampaignSubmitAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]

    def post(self, request, pk):
        try:
            campaign = Campaign.objects.get(id=pk, advertiser=request.user)
            if campaign.status not in  ['draft', 'active', 'scheduled', 'completed']:
                raise ValidationError('Can only submit draft campaigns')

            if not campaign.ads.filter(is_active=True).exists():
                raise ValidationError('Campaign must have at least one active ad')

            top_matches = CampaignChannelMatcher(campaign).get_ranked_channels(top_n=25)
            if not top_matches:
                raise ValidationError('No eligible channels found for campaign')
            
            engine = AdPlacementEngine(campaign, top_matches)
            assigned = engine.assign_placements()
            if not assigned:
                raise ValidationError('Failed to assign placements to any channels')

            escrow = EscrowService.create_campaign_escrow(
                advertiser=request.user,
                amount=campaign.initial_budget,
                campaign=campaign
            )

            try:
                campaign.status = 'in_review'
                campaign.save()
            except Exception as e:
                # Rollback escrow if campaign save fails
                EscrowService.cancel(escrow.id)
                raise ValidationError(f'Failed to save campaign: {str(e)}')

            return Response({'status': 'submitted', 'assigned_channels': len(assigned)}, status=status.HTTP_200_OK)
        except Campaign.DoesNotExist:
            return Response({'error': 'Campaign not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Failed to submit campaign: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class CampaignPauseAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]

    def post(self, request, pk):
        campaign = Campaign.objects.get(pk=pk, advertiser=request.user)
        if campaign.status != 'active':
            raise ValidationError(_("Can only pause active campaigns"))
        campaign.status = 'on_hold'
        campaign.save()
        return Response({'status': 'paused'})

class CampaignResumeAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]

    def post(self, request, pk):
        campaign = Campaign.objects.get(pk=pk, advertiser=request.user)
        if campaign.status != 'on_hold':
            raise ValidationError(_("Can only resume paused campaigns"))
        campaign.status = 'active'
        matcher = CampaignChannelMatcher(campaign)
        ranked = matcher.get_ranked_channels()
        engine = AdPlacementEngine(campaign, ranked)
        engine.activate_placements()
        campaign.save()
        return Response({'status': 'resumed'})

class CampaignStopAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]

    def post(self, request, pk):
        campaign = Campaign.objects.get(pk=pk, advertiser=request.user)
        if campaign.status not in ['active', 'on_hold']:
            raise ValidationError(_("Can only stop active or paused campaigns"))
        campaign.status = 'stopped'
        campaign.save()
        escrows = campaign.escrows.filter(status='pending')
        for escrow in escrows:
            EscrowService.cancel(escrow.id)
        return Response({'status': 'stopped'})

class BalanceDepositRequestAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]
    
    def post(self, request):
        
        amount = Decimal(request.data.get('amount'))
        mobile = request.data.get('mobile')
        payment_type = request.data.get('payment_type', 'telebirr')
        tx_ref = f"DEP-{uuid.uuid4().hex[:12].upper()}"

        # Validate inputs
        if amount < 1:
            raise ValidationError("Amount must be positive")
        if not mobile:
            raise ValidationError("Mobile number is required")

        allowed_types = ['telebirr', 'mpesa', 'cbebirr', 'ebirr']
        if payment_type not in allowed_types:
            raise ValidationError(f"Invalid payment method selected. Please choose from: {', '.join(allowed_types)}.")

        # Phone number validation
        if payment_type == 'mpesa':
            phone_regex = r'^(07\d{8}|01\d{8}|\+251[71]\d{8})$'
        else:  # telebirr, cbebirr, ebirr
            phone_regex = r'^(09\d{8}|07\d{8}|\+251[97]\d{8})$'
        
        if not re.match(phone_regex, mobile):
            if payment_type == 'mpesa':
                raise ValidationError("Mobile number must be in format 07xxxxxxxx or +2517xxxxxxxx")
            else:
                raise ValidationError("Mobile number must be in format 09xxxxxxxx, 07xxxxxxxx, or +2519xxxxxxxx/+2517xxxxxxxx")

        # Call Chapa direct charge
        data = {
            'amount': str(amount),
            'currency': 'ETB',
            'tx_ref': tx_ref,
            'mobile': mobile
        }
       
        encoder = MultipartEncoder(fields=data)
        headers = {
            'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}',
            'Content-Type': encoder.content_type
        }
        url = f"https://api.chapa.co/v1/charges?type={payment_type}"
        response = requests.post(url, data=encoder, headers=headers)

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('message', 'An unknown error occurred.')
                logger.error(f"Chapa error: {response.text}")
                if 'disabled temporarily' in error_msg.lower():
                    raise ValidationError(f"The {payment_type.capitalize()} service is temporarily unavailable. Please try another payment method.")
                raise ValidationError(f"Sorry, we couldn't start your payment: {error_msg}")
            except json.JSONDecodeError:
                logger.error(f"Chapa non-JSON response: {response.text}")
                raise ValidationError("Sorry, we couldn't start your payment. Please try again later.")

        r = response.json()
        if r.get('status') != 'success':
            error_msg = r.get('message', 'An unknown error occurred.')
            meta_msg = r.get('data', {}).get('meta', {}).get('message', '')
            if meta_msg:
                error_msg = f"{error_msg} ({meta_msg})"
            logger.error(f"Chapa failed response: {r}")
            if 'disabled temporarily' in error_msg.lower():
                raise ValidationError(f"The {payment_type.capitalize()} service is temporarily unavailable. Please try another payment method.")
            if 'charge failed to initiat' in error_msg.lower():
                raise ValidationError(f"The {payment_type.capitalize()} service is temporarily unavailable. Please try another payment method.")
            raise ValidationError(f"Sorry, we couldn't process your payment: {error_msg}")
        
        # Instruction from Chapa or default
        instruction = r.get('message', 'Please check your phone for a USSD prompt to authorize the payment.')

        return Response({
            "amount": str(amount),
            "reference": tx_ref,
            "qr_payload": "",  # Empty for USSD; use if method supports QR
            "instruction": instruction
        })

class BalanceDepositStatusAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]

    def get(self, request, tx_ref):
        logger.debug(f"Checking status for user: {request.user}, tx_ref: {tx_ref}")

        headers = {
            'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}'
        }
        url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            logger.debug(f"Chapa verify response: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Chapa verify request failed: {str(e)}")
            raise ValidationError("Unable to check payment status. Please try again or confirm manually.")

        if response.status_code != 200:
            raise ValidationError("Failed to verify payment status. Please try again or confirm manually.")

        r = response.json()
        status = r.get('data', {}).get('status', 'pending')
        if status == 'success':
            if r['data'].get('currency') != 'ETB':
                logger.error(f"Payment validation failed for tx_ref {tx_ref}: amount or currency mismatch")
                raise ValidationError("Payment details do not match. Please contact support.")
            # Credit balance
            try:
                WalletService.confirm_deposit(request.user, Decimal(r['data']['amount']), tx_ref)
                logger.info(f"Balance credited for user {request.user}, tx_ref: {tx_ref}")
                return Response({
                    'status': 'success',
                    'message': f"Your payment of ETB {r['data']['amount']} was successful and your balance has been updated!",
                    'credited': True
                })
            except Exception as e:
                logger.error(f"Failed to credit balance for tx_ref {tx_ref}: {str(e)}")
                raise ValidationError("Payment was successful, but we couldn't update your balance. Please contact support.")
        elif status == 'failed':
            raise ValidationError("Payment was not completed. Please try again or contact support.")
        else:
            return Response({
                'status': 'pending',
                'message': 'Payment is still pending. Please complete the USSD prompt on your phone.',
                'credited': False
            })
        
class BalanceDepositConfirmAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]

    def post(self, request):
        amount = Decimal(request.data.get('amount'))
        reference = request.data.get('reference')

        # Verify with Chapa before crediting
        headers = {'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}'}
        url = f"https://api.chapa.co/v1/transaction/verify/{reference}"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise ValidationError(f"Payment verification failed: {response.text}")

        r = response.json()
        if (r.get('status') != 'success' or
            r.get('data', {}).get('status') != 'success' or
            Decimal(r['data'].get('amount', 0)) != amount or
            r['data'].get('currency') != 'ETB'):
            raise ValidationError("Payment not successful or details mismatch")

        # If verified, credit balance
        WalletService.confirm_deposit(request.user, amount, reference)
        return Response({'status': 'confirmed'}, status=status.HTTP_200_OK)
    

class BalanceSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]

    def get(self, request):
        summary = BalanceService.get_balance_summary(request.user, role='advertiser')
        transactions = summary.pop('transactions', [])

        filtered_transactions = [
            tx for tx in transactions
            if tx.transaction_type not in ['spend']
        ]

        serialized = {
            **summary,
            'transactions': TransactionSerializer(filtered_transactions, many=True).data
        }
        return Response(serialized)
    
class PerformanceListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ad_placement__ad__campaign']

    def get_queryset(self):
        qs = AdPerformance.objects.filter(
            ad_placement__ad__campaign__advertiser=self.request.user
        ).prefetch_related(
            'ad_placement__ad__campaign',
            'ad_placement__channel__category',
            'ad_placement__ad',
            'ad_placement__channel'
        )
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        campaign_id = self.request.query_params.get('ad_placement__ad__campaign')
        if campaign_id:
            qs = qs.filter(ad_placement__ad__campaign_id=campaign_id)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        return qs

    def get(self, request):
        queryset = self.get_queryset()
        # Aggregate by date to avoid duplicates
        data = queryset.values('date').annotate(
            impressions=Coalesce(Sum('impressions'), Value(0), output_field=IntegerField()),
            cost=Coalesce(Sum('cost'), Value(0), output_field=DecimalField(max_digits=10, decimal_places=2)),
            clicks=Coalesce(Sum('clicks'), Value(0), output_field=IntegerField()),
            conversions=Coalesce(Sum('conversions'), Value(0), output_field=IntegerField()),
            reposts=Coalesce(Sum('reposts'), Value(0), output_field=IntegerField()),
            total_reactions=Coalesce(Sum('total_reactions'), Value(0), output_field=IntegerField()),
            total_replies=Coalesce(Sum('total_replies'), Value(0), output_field=IntegerField()),
            views=Coalesce(Sum('views'), Value(0), output_field=IntegerField()),
            forwards=Coalesce(Sum('forwards'), Value(0), output_field=IntegerField())
        ).order_by('date')
        serializer = PerformanceSerializer(data, many=True)
        return Response(serializer.data)
    

class PerformanceSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]

    def get_queryset(self):
        # Base queryset for AdPerformance owned by the current advertiser
        qs = AdPerformance.objects.filter(ad_placement__ad__campaign__advertiser=self.request.user) \
            .prefetch_related(
                'ad_placement__ad__campaign', 
                'ad_placement__channel__category',
                'ad_placement__ad__campaign__targeting_languages' # Pre-fetch M2M for language grouping
            )
        
   
        start_date_str = self.request.query_params.get('start_date')
        end_date_str = self.request.query_params.get('end_date')
        period = self.request.query_params.get('period')
        
        today = timezone.now().date() + timedelta(days=1)
        start_date = None
        end_date = None
        
        if period == 'today':
            start_date = today - timedelta(days=1)
            end_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
            end_date = today
        elif period == 'month':
            start_date = today - timedelta(days=30)
            end_date = today
        elif start_date_str and end_date_str:
             try:
                start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date() + timedelta(days=1)
             except ValueError:
                 # Handle invalid date format if necessary
                 pass
        
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            # We use date__lt (less than) if end_date was set to (date + 1 day)
            qs = qs.filter(date__lt=end_date) 
            
        return qs

    def get(self, request):
        qs = self.get_queryset()
        group_by = request.query_params.get('group_by')
        
        # --- Timeframe Setup (Refined and simplified date extraction) ---
        today = timezone.now().date()
        
        # Default start_date calculation based on period (to match get_queryset logic)
        period = request.query_params.get('period', 'month')
        if period == 'today':
            delta = timedelta(days=1)
        elif period == 'week':
            delta = timedelta(days=7)
        else: # Default to month
            delta = timedelta(days=30) 
            
        # Get start_date from URL or calculate default based on delta
        start_date_param = request.query_params.get('start_date')
        if start_date_param:
            start_date = timezone.datetime.strptime(start_date_param, '%Y-%m-%d').date()
        else:
            start_date = today - delta
        
        # Get end_date from URL or use today
        end_date_param = request.query_params.get('end_date')
        if end_date_param:
            end_date = timezone.datetime.strptime(end_date_param, '%Y-%m-%d').date()
        else:
            end_date = today

        # Recalculate delta for previous period comparison based on final chosen range
        time_diff = end_date - start_date
        prev_start_date = start_date - time_diff
        prev_end_date = start_date 


        # Helper function for metric aggregation
        def get_metrics(qs, start, end):
            # Ensure filtering is done using date__gte and date__lt
            data = qs.filter(date__gte=start, date__lte=end + timedelta(days=1)).aggregate( 
                total_cost=Coalesce(Sum('cost'), Value(Decimal('0.00'))),
                total_impressions=Coalesce(Sum('impressions'), Value(0)),
                total_clicks=Coalesce(Sum('clicks'), Value(0)),
                total_conversions=Coalesce(Sum('conversions'), Value(0)),
                total_reposts=Coalesce(Sum('reposts'), Value(0)),
                total_reactions=Coalesce(Sum('total_reactions'), Value(0)),
                total_replies=Coalesce(Sum('total_replies'), Value(0)),
                total_views=Coalesce(Sum('views'), Value(0)),
                total_forwards=Coalesce(Sum('forwards'), Value(0)),
            )
            
            # Extract and calculate rates (logic kept as provided)
            impressions = data['total_impressions'] or 0
            clicks = data['total_clicks'] or 0
            conversions = data['total_conversions'] or 0
            reactions = data['total_reactions'] or 0
            replies = data['total_replies'] or 0
            forwards = data['total_forwards'] or 0
            reposts = data['total_reposts']
            views = data['total_views'] or 0
            cost = data['total_cost'] or 0
            
            return {
                'total_cost': float(cost),
                'total_impressions': impressions,
                'total_clicks': clicks,
                'total_conversions': conversions,
                'total_reposts': reposts,
                'total_reactions': reactions,
                'total_replies': replies,
                'total_views': views,
                'total_forwards': forwards,
                'ctr': round((clicks / impressions * 100), 2) if impressions else 0,
                'cpc': round((cost / clicks), 2) if clicks else 0,
                'cpm': round((cost / impressions * 1000) if impressions else 0, 2),
                'conversion_rate': round((conversions / clicks * 100) if clicks else 0, 2),
                'engagement_rate': round(((clicks + reactions + replies + forwards) / impressions * 100) if impressions else 0, 2),
                'soft_ctr': round(((clicks + reactions + replies) / impressions * 100), 2) if impressions else 0,
                'viewability_rate': round((views / impressions * 100) if impressions else 0, 2),
                'virality_rate': round((forwards / views * 100) if views else 0, 2),
            }

        # Helper function for calculating percentage change
        def format_change(current, previous):
            if previous == 0:
                return "+∞%" if current > 0 else "0%", "positive" if current > 0 else "neutral", "↑" if current > 0 else ""
            change = ((current - previous) / previous) * 100
            return f"{change:+.1f}%", "positive" if change >= 0 else "negative", "↑" if change >= 0 else "↓"

        # --- Grouped Responses ---

        if group_by == 'campaign' or group_by == 'category' or group_by == 'language':
            if group_by == 'campaign':
                group_field = 'ad_placement__ad__campaign__name'
                label = 'campaign'
            elif group_by == 'category':
                group_field = 'ad_placement__channel__category__name'
                label = 'category'
            elif group_by == 'language':
                # --Group by the name of the language targeted by the campaign
                group_field = 'ad_placement__ad__campaign__targeting_languages__name' 
                label = 'language'

            data = qs.values(group_field).annotate(
                # Aggregation fields (copied from get_metrics)
                total_cost=Coalesce(Sum('cost'), Value(Decimal('00'))),
                total_impressions=Coalesce(Sum('impressions'), Value(0)),
                total_clicks=Coalesce(Sum('clicks'), Value(0)),
                total_conversions=Coalesce(Sum('conversions'), Value(0)),
                total_reposts=Coalesce(Sum('reposts'), Value(0)),
                total_reactions=Coalesce(Sum('total_reactions'), Value(0)),
                total_replies=Coalesce(Sum('total_replies'), Value(0)),
                total_views=Coalesce(Sum('views'), Value(0)),
                total_forwards=Coalesce(Sum('forwards'), Value(0)),
            )
            data = data.order_by('-total_impressions')
            
            result = []
            for item in data:
                impressions = item['total_impressions']
                clicks = item['total_clicks']
                views = item['total_views']
                cost = item['total_cost']
                reactions = item['total_reactions']
                replies = item['total_replies']
                conversions = item['total_conversions']
                forwards = item['total_forwards']
                
                result.append({
                    label: item[group_field] or '-', # Use '-' for Null M2M groups
                    'total_cost': float(cost),
                    'total_impressions': impressions,
                    'total_clicks': clicks,
                    'total_conversions': conversions,
                    'total_reposts': item['total_reposts'],
                    'total_reactions': reactions,
                    'total_replies': replies,
                    'total_views': views,
                    'total_forwards': forwards,
                    # Calculate rates based on aggregated values
                    'ctr': round((clicks / impressions * 100), 2) if impressions else 0,
                    'cpc': round((cost / clicks), 2) if clicks else 0,
                    'cpm': round((cost / impressions * 1000) if impressions else 0, 2),
                    'conversion_rate': round((conversions / clicks * 100) if clicks else 0, 2),
                    'engagement_rate': round(((reactions + replies) / impressions * 100) if impressions else 0, 2),
                    'soft_ctr': round(((clicks + reactions + replies) / impressions * 100) if impressions else 0, 2),
                    'viewability_rate': round((views / impressions * 100) if impressions else 0, 2),
                    'virality_rate': round((forwards / views * 100) if views else 0, 2),
                })
            
            return Response(result)

        # --- Main Summary Response (No Grouping) ---
        else:
            current_metrics = get_metrics(qs, start_date, end_date)
            previous_metrics = get_metrics(qs, prev_start_date, prev_end_date)
            
            # Calculate total number of active campaigns
            active_campaign_count = Campaign.objects.filter(
                advertiser=request.user, 
                status=AdStatus.ACTIVE
            ).count()

            result = {
                'active_campaign_count': active_campaign_count, # Include the count
                **current_metrics,
                'spend_change': format_change(current_metrics['total_cost'], previous_metrics['total_cost']),
                'impressions_change': format_change(current_metrics['total_impressions'], previous_metrics['total_impressions']),
                'clicks_change': format_change(current_metrics['total_clicks'], previous_metrics['total_clicks']),
                'ctr_change': format_change(current_metrics['ctr'], previous_metrics['ctr']),
                'conversion_rate_change': format_change(current_metrics['conversion_rate'], previous_metrics['conversion_rate']),
                'engagement_rate_change': format_change(current_metrics['engagement_rate'], previous_metrics['engagement_rate']),
                'soft_ctr_change': format_change(current_metrics['soft_ctr'], previous_metrics['soft_ctr']),
                'viewability_rate_change': format_change(current_metrics['viewability_rate'], previous_metrics['viewability_rate']),
                'virality_rate_change': format_change(current_metrics['virality_rate'], previous_metrics['virality_rate']),
                'cpc_change': format_change(current_metrics['cpc'], previous_metrics['cpc']),
            }
            return Response(result)


class PerformanceExportAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdvertiser]

    def get_queryset(self):
        qs = AdPerformance.objects.filter(ad_placement__ad__campaign__advertiser=self.request.user) \
            .prefetch_related('ad_placement__ad__campaign', 'ad_placement__channel__category') \
            .prefetch_related('ad_placement__ad', 'ad_placement__channel')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        return qs

    def get(self, request):
        qs = self.get_queryset()
        group_by = request.query_params.get('group_by')
        data = []

        aggregates = {
            'total_impressions': Coalesce(Sum('impressions'), 0),
            'total_clicks': Coalesce(Sum('clicks'), 0),
            'total_conversions': Coalesce(Sum('conversions'), 0),
            'total_reposts': Coalesce(Sum('reposts'), 0),
            'total_cost': Coalesce(Sum('cost'), Decimal('00')),
            'total_reactions': Coalesce(Sum('total_reactions'), 0),
            'total_replies': Coalesce(Sum('total_replies'), 0),
            'total_views': Coalesce(Sum('views'), 0),
            'total_forwards': Coalesce(Sum('forwards'), 0),
            'ctr': ExpressionWrapper(
                Coalesce(Sum('clicks') * Value(1.0) / Sum('impressions'), Value(0)) * 100,
                output_field=FloatField()
            ),
            'cpc': ExpressionWrapper(
                Coalesce(Sum('cost') / Sum('clicks'), Value(0)),
                output_field=FloatField()
            ),
            'cpm': ExpressionWrapper(
                Coalesce(Sum('cost') / Sum('impressions') * 1000, Value(0)),
                output_field=FloatField()
            ),
        }

        if group_by == 'campaign':
            grouped = qs.values('ad_placement__ad__campaign__name').annotate(**aggregates)
            for item in grouped:
                item['group'] = item.pop('ad_placement__ad__campaign__name')
                data.append(item)
        elif group_by == 'category':
            grouped = qs.values('ad_placement__channel__category__name').annotate(**aggregates)
            for item in grouped:
                item['group'] = item.pop('ad_placement__channel__category__name')
                data.append(item)
        else:
            for perf in qs:
                data.append({
                    'date': perf.date,
                    'impressions': perf.impressions,
                    'clicks': perf.clicks,
                    'conversions': perf.conversions,
                    'reposts': perf.reposts,
                    'cost': perf.cost,
                    'total_reactions': perf.total_reactions,
                    'total_replies': perf.total_replies,
                    'views': perf.views,
                    'forwards': perf.forwards,
                    'ctr': perf.ctr,
                    'cpc': perf.cpc,
                    'cpm': perf.cpm,
                    'conversion_rate': perf.conversion_rate,
                    'engagement_rate': perf.engagement_rate,
                    'soft_ctr': perf.soft_ctr,
                    'viewability_rate': perf.viewability_rate,
                    'virality_rate': perf.virality_rate,
                })

        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Performance')
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=sonicAdz_performance_report.xlsx'
        return response


































































































# from io import BytesIO
# import pandas as pd
# from decimal import Decimal
# import uuid
# from rest_framework import serializers
# from rest_framework import viewsets, permissions, status
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from rest_framework.exceptions import ValidationError, PermissionDenied
# from django_filters.rest_framework import DjangoFilterBackend
# from django.db.models import Sum, F, Value, FloatField
# from django.db.models.functions import Coalesce
# from django.db.models.expressions import ExpressionWrapper
# from django.http import HttpResponse
# from core.models import Campaign, Ad, AdPerformance, Category, Language, AdPlacement
# from creators.models import CreatorChannel
# from core.services.matching_engine import CampaignChannelMatcher
# from core.services.ad_placement_engine import AdPlacementEngine
# from payments.services.payment_service import WalletService, EscrowService
# from payments.services.balance_service import BalanceService
# from api.serializers.campaigns import CampaignSerializer, PerformanceSerializer
# from api.permissions.campaigns import IsAdvertiser, IsCampaignOwnerOrReadOnly, IsAdminUser
# from django.utils.translation import gettext_lazy as _

# # Views
# class CampaignViewSet(viewsets.ModelViewSet):
#     """
#     API ViewSet for managing advertiser campaigns.
#     Supports create, list, retrieve, update (edit), delete, pause, resume, stop, submit.
#     Optimizations: select_related and prefetch_related for related fields.
#     """
#     serializer_class = CampaignSerializer
#     permission_classes = [IsAdvertiser]
#     queryset = Campaign.objects.none()  # Default empty

#     def get_queryset(self):
#         return Campaign.objects.filter(advertiser=self.request.user, is_active=True) \
#             .select_related('advertiser') \
#             .prefetch_related('targeting_languages', 'targeting_categories', 'ads')

#     def perform_create(self, serializer):
#         campaign = serializer.save()
#         # Placeholder for payment gateway integration (e.g., Stripe)
#         # For now, assume local deposit has been handled separately; escrow created on submit

#     def perform_update(self, serializer):
#         instance = self.get_object()
#         if instance.status not in ['on_hold', 'stopped']:
#             raise PermissionDenied(_("Can only edit paused or stopped campaigns"))
#         serializer.save()

#     def perform_destroy(self, instance):
#         if instance.status not in ['draft', 'declined', 'stopped', 'on_hold']:
#             raise PermissionDenied(_("Can only delete draft, declined, stopped, or paused campaigns"))
#         instance.is_active = False
#         instance.save()

#     @action(detail=True, methods=['post'], url_path='submit')
#     def submit(self, request, pk=None):
#         campaign = self.get_object()
#         if campaign.status != 'draft':
#             raise ValidationError(_("Can only submit draft campaigns"))
#         # Create escrow for the campaign
#         escrow = EscrowService.create_campaign_escrow(
#             advertiser=request.user,
#             amount=campaign.initial_budget
#         )
#         escrow.campaign = campaign
#         escrow.save()
#         campaign.status = 'in_review'
#         campaign.save()
#         return Response({'status': 'submitted for review'})

#     @action(detail=True, methods=['post'], url_path='pause')
#     def pause(self, request, pk=None):
#         campaign = self.get_object()
#         if campaign.status != 'active':
#             raise ValidationError(_("Can only pause active campaigns"))
#         campaign.status = 'on_hold'
#         campaign.save()
#         return Response({'status': 'paused'})

#     @action(detail=True, methods=['post'], url_path='resume')
#     def resume(self, request, pk=None):
#         campaign = self.get_object()
#         if campaign.status != 'on_hold':
#             raise ValidationError(_("Can only resume paused campaigns"))
#         campaign.status = 'active'
#         # Trigger placement if needed
#         matcher = CampaignChannelMatcher(campaign)
#         ranked = matcher.get_ranked_channels()
#         engine = AdPlacementEngine(campaign, ranked)
#         engine.activate_placements()  # Assumes escrow exists
#         campaign.save()
#         return Response({'status': 'resumed'})

#     @action(detail=True, methods=['post'], url_path='stop')
#     def stop(self, request, pk=None):
#         campaign = self.get_object()
#         if campaign.status not in ['active', 'on_hold']:
#             raise ValidationError(_("Can only stop active or paused campaigns"))
#         campaign.status = 'stopped'
#         campaign.save()
#         # Optionally, cancel escrow if remaining
#         escrows = campaign.escrows.filter(status='pending')
#         for escrow in escrows:
#             EscrowService.cancel(escrow.id)
#         return Response({'status': 'stopped'})

# class BalanceViewSet(viewsets.GenericViewSet):
#     """
#     API ViewSet for advertiser balance management, including deposit and summary.
#     """
#     permission_classes = [IsAdvertiser]

#     @action(detail=False, methods=['post'], url_path='deposit')
#     def deposit(self, request):
#         amount = Decimal(request.data.get('amount'))
#         if amount <= 0:
#             raise ValidationError(_("Deposit amount must be positive"))
#         reference = request.data.get('reference', f'DEP-{uuid.uuid4()}')
#         # Placeholder for payment gateway (e.g., Stripe integration)
#         # For now, handle locally
#         WalletService.deposit(request.user, amount, reference)
#         return Response({'status': 'deposited', 'amount': amount}, status=status.HTTP_200_OK)

#     @action(detail=False, methods=['get'], url_path='summary')
#     def summary(self, request):
#         summary = BalanceService.get_balance_summary(request.user, role='advertiser')
#         return Response(summary)

# class PerformanceViewSet(viewsets.ReadOnlyModelViewSet):
#     """
#     API ViewSet for viewing ad performance.
#     Supports list (with pagination, date range), summary (aggregations, group by campaign/category), export (Excel).
#     Optimizations: select_related and prefetch_related.
#     """
#     serializer_class = PerformanceSerializer
#     permission_classes = [IsAdvertiser]
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['ad_placement__ad__campaign']

#     def get_queryset(self):
#         qs = AdPerformance.objects.filter(ad_placement__ad__campaign__advertiser=self.request.user) \
#             .select_related('ad_placement__ad__campaign', 'ad_placement__channel__category') \
#             .prefetch_related('ad_placement__ad', 'ad_placement__channel')
#         start_date = self.request.query_params.get('start_date')
#         end_date = self.request.query_params.get('end_date')
#         if start_date:
#             qs = qs.filter(date__gte=start_date)
#         if end_date:
#             qs = qs.filter(date__lte=end_date)
#         return qs

#     @action(detail=False, methods=['get'], url_path='summary')
#     def summary(self, request):
#         qs = self.get_queryset()
#         group_by = request.query_params.get('group_by')
#         aggregates = self._get_aggregates()

#         if group_by == 'campaign':
#             qs = qs.values('ad_placement__ad__campaign__name').annotate(**aggregates).order_by('ad_placement__ad__campaign__name')
#         elif group_by == 'category':
#             qs = qs.values('ad_placement__channel__category__name').annotate(**aggregates).order_by('ad_placement__channel__category__name')
#         else:
#             qs = qs.aggregate(**aggregates)
#             return Response(qs)

#         return Response(list(qs))

#     def _get_aggregates(self):
#         return {
#             'total_impressions': Coalesce(Sum('impressions'), 0),
#             'total_clicks': Coalesce(Sum('clicks'), 0),
#             'total_conversions': Coalesce(Sum('conversions'), 0),
#             'total_reposts': Coalesce(Sum('reposts'), 0),
#             'total_cost': Coalesce(Sum('cost'), Decimal('00')),
#             'total_reactions': Coalesce(Sum('total_reactions'), 0),
#             'total_replies': Coalesce(Sum('total_replies'), 0),
#             'total_views': Coalesce(Sum('views'), 0),
#             'total_forwards': Coalesce(Sum('forwards'), 0),
#             'ctr': ExpressionWrapper(
#                 Coalesce(Sum('clicks') * Value(1.0) / Sum('impressions'), Value(0)) * 100,
#                 output_field=FloatField()
#             ),
#             'cpc': ExpressionWrapper(
#                 Coalesce(Sum('cost') / Sum('clicks'), Value(0)),
#                 output_field=FloatField()
#             ),
#             'cpm': ExpressionWrapper(
#                 Coalesce(Sum('cost') / Sum('impressions') * 1000, Value(0)),
#                 output_field=FloatField()
#             ),
#             # Add other computed fields similarly if needed
#         }

#     @action(detail=False, methods=['get'], url_path='export')
#     def export(self, request):
#         qs = self.get_queryset()
#         group_by = request.query_params.get('group_by')
#         data = []

#         if group_by == 'campaign':
#             aggregates = self._get_aggregates()
#             grouped = qs.values('ad_placement__ad__campaign__name').annotate(**aggregates)
#             for item in grouped:
#                 item['group'] = item.pop('ad_placement__ad__campaign__name')
#                 data.append(item)
#         elif group_by == 'category':
#             aggregates = self._get_aggregates()
#             grouped = qs.values('ad_placement__channel__category__name').annotate(**aggregates)
#             for item in grouped:
#                 item['group'] = item.pop('ad_placement__channel__category__name')
#                 data.append(item)
#         else:
#             # Raw data with computed fields
#             for perf in qs:
#                 data.append({
#                     'date': perf.date,
#                     'impressions': perf.impressions,
#                     'clicks': perf.clicks,
#                     'conversions': perf.conversions,
#                     'reposts': perf.reposts,
#                     'cost': perf.cost,
#                     'total_reactions': perf.total_reactions,
#                     'total_replies': perf.total_replies,
#                     'views': perf.views,
#                     'forwards': perf.forwards,
#                     'ctr': perf.ctr,
#                     'cpc': perf.cpc,
#                     'cpm': perf.cpm,
#                     'conversion_rate': perf.conversion_rate,
#                     'engagement_rate': perf.engagement_rate,
#                     'soft_ctr': perf.soft_ctr,
#                     'viewability_rate': perf.viewability_rate,
#                     'virality_rate': perf.virality_rate,
#                 })

#         df = pd.DataFrame(data)
#         output = BytesIO()
#         with pd.ExcelWriter(output, engine='openpyxl') as writer:
#             df.to_excel(writer, index=False, sheet_name='Performance')
#         output.seek(0)
#         response = HttpResponse(
#             output.read(),
#             content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#         )
#         response['Content-Disposition'] = 'attachment; filename=performance_report.xlsx'
#         return response