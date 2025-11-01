from django.conf import settings
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from rest_framework.views import APIView
from django.http import JsonResponse
from collections import defaultdict
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from rest_framework import serializers
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from django.db.models import (
    Sum, 
    Count, 
    Q, F, 
    Prefetch, 
    DecimalField, 
    ExpressionWrapper,
    )
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models.functions import ExtractWeek, ExtractYear
from decimal import Decimal, InvalidOperation

from core.utils.security import decrypt_activation_code
from miniapp.utils import TelegramVerificationUtil
from payments.services import WithdrawalService, BalanceService
from payments.utils import get_creator_share


from users.models import UserType
from creators.models import (
    CreatorChannel,
    CreatorReputation,
)
from payments.models import (
    Balance,
    Escrow,
    Transaction,
    PaymentMethodType,
    UserPaymentMethod,
    WithdrawalRequest,
)
from core.models import (
    AdPlacement,
    AdPerformance,
    Category,
    Language,
    Notification,
    
)
from api.serializers.creators import (
    ChannelSerializer,
    ChannelUpdateSerializer,
    AdPlacementSerializer,
    DashboardSerializer,
    CategorySerializer,
    LanguageSerializer,
    ChannelCreateSerializer,
    ChannelVerificationSerializer,
    PaymentMethodTypeSerializer,
    UserPaymentMethodSerializer,
    WithdrawalRequestSerializer,
)
from api.serializers.payments import TransactionSerializer
from api.serializers.notifications import NotificationSerializer


class IsCreatorUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == UserType.CREATOR



class DashboardAPIView(APIView):
    permission_classes = [IsCreatorUser, permissions.IsAuthenticated]

    def get(self, request):
            
        user = request.user
        now = timezone.now()
        first_day_of_month = now.replace(day=1).date()
        next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1).date()
        last_day_of_month = next_month - timedelta(days=1)
        time_threshold = now - timedelta(weeks=4)

        # 1. Top channels by subscribers
        top_channels = CreatorChannel.objects.filter(
            owner=user,
            is_active=True
        ).order_by('-subscribers')[:1]

        # 2. Active ad placements with recent performance
        active_ad_placements = AdPlacement.objects.filter(
            channel__owner=user,
            status__in=['running', 'approved'],
            is_active=True
        ).select_related('ad', 'channel').prefetch_related(
            Prefetch(
                'performance',
                queryset=AdPerformance.objects.filter(date__gte=time_threshold)
            )
        )[:5]


        CREATOR_SHARE_MULTIPLIER = Decimal('1') - (Decimal(settings.PLATFORM_FEE) / Decimal('100'))
        monthly_data = (
            AdPerformance.objects.filter(
                ad_placement__channel__owner=user,
                date__range=(first_day_of_month, last_day_of_month)
            )
            .annotate(
                creator_earning=ExpressionWrapper(
                    F('cost') * CREATOR_SHARE_MULTIPLIER,
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
            .values('date', 'creator_earning')
        )

        weekly_totals = defaultdict(Decimal)

        for item in monthly_data:
            date = item['date']
            earning = item['creator_earning']
            

            week_of_month = ((date.day - 1) // 7) + 1
            weekly_totals[week_of_month] += earning


        chart_data = []
        week_labels = []
        week_ranges = []

        for week_num in range(1, 5):
            chart_data.append(round(float(weekly_totals.get(week_num, 0)), 2))
            week_labels.append(f"W{week_num}")

            start_day = (week_num - 1) * 7 + 1
            end_day = min(start_day + 6, last_day_of_month.day)
            week_ranges.append(f"{start_day}–{end_day}")

        balance_info = BalanceService.get_balance_summary(user, role='creator')

   
        payment_methods = UserPaymentMethod.objects.filter(user=user, is_active=True)

 
        recent_transactions = Transaction.objects.filter(user=user, sub_balance='available').order_by('-timestamp')[:6]

        
        activity_logs = LogEntry.objects.filter(user_id=user.id).order_by('-action_time')[:6]
        
        notifications = Notification.active_objects.filter(
            user=user,
            is_read=False,
            is_active=True
        ).order_by('-created_at')
        
        # notifications.update(is_read=True) 
        
        

        # Prepare and serialize data
        context = {
            'top_channels': top_channels,
            'active_ad_placements': active_ad_placements,
            'earning': {
                'balance': balance_info['available'],
                'locked': balance_info['escrow'],
                'pending_balance': balance_info['escrow'],
            },
            'payment_methods': payment_methods,
            'recent_transactions': recent_transactions,
            'chart_data': chart_data,
            'week_labels': week_labels,
            'week_ranges': week_ranges,
            'activity_logs': activity_logs,
            'notifications': NotificationSerializer(notifications, many=True).data,
            'unread_count': Notification.active_objects.filter(user=user, is_read=False).count(),
        }

        serializer = DashboardSerializer(context)
        return Response(serializer.data)
    
  

class ChannelsAPIView(APIView):
    permission_classes = [IsCreatorUser, permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        channels = CreatorChannel.objects.filter(
            owner=user,
            is_active=True
        ).prefetch_related(
            'language',
            'category',
            Prefetch(
                'ad_placements',
                queryset=AdPlacement.objects.filter(is_active=True)
            )
        )

        serializer = ChannelSerializer(channels, many=True)
        return Response(serializer.data)

class ChannelDetailAPIView(APIView):
    permission_classes = [IsCreatorUser, permissions.IsAuthenticated]

    def get_object(self, id, user):
        try:
            return CreatorChannel.objects.get(id=id, owner=user, is_active=True)
        except CreatorChannel.DoesNotExist:
            return None

    def get(self, request, id):
        channel = self.get_object(id=id, user=request.user)
        if not channel:
            return Response({'error': 'Channel not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ChannelSerializer(channel)
        return Response(serializer.data)

    def patch(self, request, id):
        """Partial update of editable fields only"""
        channel = self.get_object(id=id, user=request.user)
        if not channel:
            return Response({'error': 'Channel not found'}, status=status.HTTP_404_NOT_FOUND)

        allowed_fields = ['min_cpm', 'language', 'repost_preference_frequency', 'repost_preference', 'auto_publish']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = ChannelUpdateSerializer(channel, data=data, partial=True)
        # Log the action
        LogEntry.objects.log_action(
            user_id=request.user.id,
            content_type_id=ContentType.objects.get_for_model(CreatorChannel).pk,
            object_id=channel.pk,
            object_repr=str(channel),
            action_flag=CHANGE,
            change_message=f"Updated channel {channel.channel_link.replace('https://t.me/', '@')}"
        )
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Channel updated successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id):
        """Full update (excluding activation_code, status)"""
        channel = self.get_object(id=id, user=request.user)
        if not channel:
            return Response({'error': 'Channel not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ChannelUpdateSerializer(channel, data=request.data)
        # Log the action
        LogEntry.objects.log_action(
            user_id=request.user.id,
            content_type_id=ContentType.objects.get_for_model(CreatorChannel).pk,
            object_id=channel.pk,
            object_repr=str(channel),
            action_flag=CHANGE,
            change_message=f"Updated channel {channel.channel_link.replace('https://t.me/', '@')}"
        )
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Channel fully updated'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, id):
        """Soft delete the channel"""
        channel = self.get_object(id, request.user)
        if not channel:
            return Response({'error': 'Channel not found'}, status=status.HTTP_404_NOT_FOUND)
        channel.is_active = False
        LogEntry.objects.log_action(
            user_id=request.user.id,
            content_type_id=ContentType.objects.get_for_model(CreatorChannel).pk,
            object_id=channel.pk,
            object_repr=str(channel),
            action_flag=DELETION,
            change_message=f"Deleted channel {channel.channel_link}"
        )
        
        channel.channel_link = f"{channel.channel_link}_deleted_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        channel.status = CreatorChannel.ChannelStatus.DELETED
        channel.save()

        return Response({'message': 'Channel deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


class VerifyChannelAPIView(APIView):
    permission_classes = [IsCreatorUser, permissions.IsAuthenticated]

    def post(self, request, channel_id=None):
        # Priority: use activation_code from request body
        activation_code = request.data.get("activation_code")

        # Fallback: look up activation code by channel_id from URL
        if not activation_code and channel_id:
            try:
                channel = CreatorChannel.objects.get(id=channel_id)
                activation_code = channel.activation_code
            except CreatorChannel.DoesNotExist:
                return Response({"error": "Channel not found for provided ID."}, status=404)

        if not activation_code:
            return Response({"error": "Missing activation code"}, status=400)

        decrypted = decrypt_activation_code(activation_code)
        if not decrypted:
            return Response({"error": "Invalid or expired activation code"}, status=400)

        channel_username = decrypted.get("channel_link")
        if not channel_username:
            return Response({"error": "Missing channel username in activation code"}, status=400)

        try:
            verifier = TelegramVerificationUtil(settings.BOT_SECRET_TOKEN)
            telegram_data = verifier.fetch_channel_data_if_bot_admin(channel_username)

            channel = CreatorChannel.objects.get(activation_code=activation_code)

            channel.channel_id = telegram_data["channel_id"]
            channel.title = telegram_data["title"]
            channel.subscribers = telegram_data["subscribers"]
            channel.status = CreatorChannel.ChannelStatus.VERIFIED if telegram_data.get('can_post') else CreatorChannel.ChannelStatus.PENDING
            channel.is_active = True
            if telegram_data.get("pp_url", ""):
                channel.pp_url = telegram_data.get("pp_url") 
            channel.save()
            if telegram_data.get('can_post'):
                message = "🎉 Channel verified successfully!"
            else:
                message = "Channel verified! but you still need to enable Post Message permission to be eligible for ad placements."
            return Response({
                "message": message,
                "data": {
                    "channel_id": channel.channel_id,
                    "title": channel.title,
                    "subscribers": channel.subscribers,
                    "status": channel.status
                }
            })

        except CreatorChannel.DoesNotExist:
            return Response({"error": "Channel not registered yet."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
    
class ConnectChannelAPIView(APIView):
    permission_classes = [IsCreatorUser, permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChannelCreateSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            channel = serializer.save()

            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(CreatorChannel).pk,
                object_id=channel.pk,
                object_repr=str(channel),
                action_flag=ADDITION,
                change_message=f"Created channel {channel.channel_link}"
            )

            verification_link = channel.activation_code

            return Response({
                "ok": True,
                "message": "Channel submitted! Check telegram bot to continue verification.",
                "verification_link": verification_link
            }, status=status.HTTP_201_CREATED)

        return Response({"ok": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
       

class AdsAPIView(APIView):
    permission_classes = [IsCreatorUser, permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        status_filter = request.query_params.get('status', None)
        
        base_query = AdPlacement.objects.filter(
            channel__owner=user,
            is_active=True,
            status__in=['pending', 'approved', 'running']
        ).select_related('ad', 'channel')
        
        if status_filter:
            base_query = base_query.filter(status=status_filter)
        
        placements = base_query.order_by('-placed_at')
        
        serializer = AdPlacementSerializer(placements, many=True)
        return Response(serializer.data)

class AdDetailAPIView(APIView):
    permission_classes = [IsCreatorUser, permissions.IsAuthenticated]

    def get(self, request, ad_id):
        try:
            placement = AdPlacement.objects.get(
                id=ad_id,
                channel__owner=request.user,
                is_active=True
            )
        except AdPlacement.DoesNotExist:
            return Response(
                {'error': 'Ad placement not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get performance data
        performance = AdPerformance.objects.filter(
            ad_placement=placement
        ).order_by('-date')
        
        # Calculate totals
        CREATOR_SHARE_MULTIPLIER = Decimal('1') - (Decimal(settings.PLATFORM_FEE) / Decimal('100'))
        totals = performance.aggregate(
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks'),
            total_earnings=Sum(F('cost') * CREATOR_SHARE_MULTIPLIER, output_field=DecimalField())
        )
        
        data = {
            'ad_placement': placement,
            'performance': performance,
            'totals': totals
        }
        
        return Response(data)



class PaymentMethodsChoice(APIView):
    def get(self, request):
        user = request.user
        try:
            # Get IDs of payment methods the user already added
            added_method_ids = UserPaymentMethod.objects.filter(user=user, is_active=True).values_list('payment_method_type_id', flat=True)
        except Exception as e:
            added_method_ids = []
            
        # Filter out the added ones
        choices = PaymentMethodType.objects.filter(is_active=True).exclude(id__in=added_method_ids)
        # choices = PaymentMethodType.objects.filter(is_active=True)
        serializer = PaymentMethodTypeSerializer(choices, many=True)
        return Response(serializer.data)
       
# class PaymentAPIView(APIView):
#     permission_classes = [IsCreatorUser, permissions.IsAuthenticated]

#     def get(self, request):
#         user = request.user

#         # Use the centralized balance summary
#         balance_info = BalanceService.get_balance_summary(user, role='creator')

#         # Active payment methods
#         methods = UserPaymentMethod.objects.filter(user=user, is_active=True)
#         methods_data = UserPaymentMethodSerializer(methods, many=True).data

#         # Last withdrawal
#         last_withdrawal = WithdrawalRequest.objects.filter(
#             user_payment_method__user=user,
#             status__in=[
#                 WithdrawalRequest.RequestStatus.APPROVED,
#                 WithdrawalRequest.RequestStatus.COMPLETED,
#                 WithdrawalRequest.RequestStatus.PENDING,
#             ]
#         ).order_by('-created_at').first()

#         last_transaction = None
#         if last_withdrawal:
#             last_transaction = {
#                 'amount': str(last_withdrawal.amount),
#                 'account_ending': last_withdrawal.user_payment_method.account_number[-4:]
#                     if last_withdrawal.user_payment_method.account_number else "****",
#                 'status': last_withdrawal.status,
#                 'created_at': last_withdrawal.created_at,
#             }

#         # All transactions
#         transactions = Transaction.objects.filter(user=user).order_by('-timestamp')
#         transaction_data = [{
#             'transaction_type': tx.transaction_type,
#             'transaction_type_display': tx.get_transaction_type_display(),
#             'amount': str(tx.amount),
#             'note': tx.transaction_reference,
#             'created_at': tx.timestamp,
#         } for tx in transactions]

#         return Response({
#             'balance': {
#                 'available': str(balance_info['available']),
#                 'locked': str(balance_info['locked']),
#                 'pending_balance': str(balance_info['locked']),
#             },
#             'payment_methods': methods_data,
#             'transaction': last_transaction,
#             'transactions': transaction_data
#         })

#     def post(self, request):
#         serializer = UserPaymentMethodSerializer(
#             data=request.data,
#             context={'request': request}
#         )
#         if serializer.is_valid():
#             payment_method = serializer.save()
#             user_payment_methods = UserPaymentMethod.objects.filter(user=request.user, is_active=True)

#             # Default logic
#             if user_payment_methods.count() == 1:
#                 payment_method.is_default = True
#                 payment_method.save()
#             else:
#                 payment_method.is_default = False
#                 payment_method.save()

#             # Logging
#             method_type = payment_method.payment_method_type
#             # Ensure the phone number or account number is a string and handle it safely
#             if method_type.category == method_type.MethodCategory.BANK and payment_method.account_number:
#                 display_ref = payment_method.account_number[-4:]  # Last 4 digits of the account number
#             elif payment_method.phone_number:
#                 # If the phone_number is a string, take the last 4 digits
#                 display_ref = str(payment_method.phone_number)[-4:]
#             else:
#                 display_ref = "****"  # Fallback if neither is available

#             LogEntry.objects.log_action(
#                 user_id=request.user.id,
#                 content_type_id=ContentType.objects.get_for_model(UserPaymentMethod).pk,
#                 object_id=payment_method.pk,
#                 object_repr=str(payment_method),
#                 action_flag=ADDITION,
#                 change_message=f"Added {method_type.category} payment method: {method_type.name} ({display_ref})"
#             )

#             return Response({
#                 'ok': True,
#                 'message': 'Payment method added successfully',
#                 'payment_method': UserPaymentMethodSerializer(payment_method).data
#             }, status=status.HTTP_201_CREATED)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     def patch(self, request, method_id):

#         if not method_id:
#             return Response({'error': 'Payment method ID is required'}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             # Fetch the payment method for the given user
#             payment_method = UserPaymentMethod.objects.get(id=method_id, user=request.user)
#         except UserPaymentMethod.DoesNotExist:
#             raise NotFound({'error': 'Payment method not found'})

#         # Serialize the incoming data to update the existing object
#         serializer = UserPaymentMethodSerializer(payment_method, data=request.data, partial=True, context={'request': request})
        
#         if serializer.is_valid():
#             updated_payment_method = serializer.save()

#             # Handle the default payment method logic
#             user_payment_methods = UserPaymentMethod.objects.filter(user=request.user, is_active=True)

#             # If setting the method as default
#             if updated_payment_method.is_default:
#                 if user_payment_methods.count() == 1:
#                     updated_payment_method.is_default = True  # First method will be the default
#                     updated_payment_method.save()
#                 else:
#                     # If another default exists, we don't change the current method
#                     user_payment_methods.update(is_default=False)
#                     updated_payment_method.is_default = True
#                     updated_payment_method.save()

#             # Log the update event
#             method_type = updated_payment_method.payment_method_type
#             display_ref = (
#                 str(updated_payment_method.account_number)[-4:]
#                 if method_type.category == method_type.MethodCategory.BANK and updated_payment_method.account_number
#                 else str(updated_payment_method.phone_number)[-4:]
#                 if updated_payment_method.phone_number
#                 else "****"
#             )

#             LogEntry.objects.log_action(
#                 user_id=request.user.id,
#                 content_type_id=ContentType.objects.get_for_model(UserPaymentMethod).pk,
#                 object_id=updated_payment_method.pk,
#                 object_repr=str(updated_payment_method),
#                 action_flag=CHANGE,
#                 change_message=f"Updated {method_type.category} payment method: {method_type.name} ({display_ref})"
#             )

#             return Response({
#                 'ok': True,
#                 'message': 'Payment method updated successfully',
#                 'payment_method': UserPaymentMethodSerializer(updated_payment_method).data
#             }, status=status.HTTP_200_OK)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
#     def delete(self, request, method_id):
#         if not method_id:
#             return Response({'error': 'Method ID is required'}, status=400)

#         try:
#             method = UserPaymentMethod.objects.get(id=method_id, user=request.user)

#             if UserPaymentMethod.objects.filter(user=request.user, is_active=True).count() == 1:
#                 return Response(
#                     {'error': 'Cannot delete your only payment method'},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )

#              # Reset default if needed
#             if method.is_default:
#                 new_default = UserPaymentMethod.objects.filter(
#                     user=request.user,
#                     is_active=True
#                 ).exclude(id=method.id).first()
#                 if new_default:
#                     new_default.is_default = True
#                     new_default.save()
                    
#             method.is_active = False
#             method.is_default = False
#             method.account_name = f"{method.account_name}--DELETE-{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
#             method.save()

#             method_type = method.payment_method_type
#             display_ref = (
#                 method.account_number[-4:]
#                 if method_type.category == method_type.MethodCategory.BANK and method.account_number
#                 else method.phone_number[-4:] if method.phone_number
#                 else "****"
#             )

#             LogEntry.objects.log_action(
#                 user_id=request.user.id,
#                 content_type_id=ContentType.objects.get_for_model(UserPaymentMethod).pk,
#                 object_id=method.pk,
#                 object_repr=str(method),
#                 action_flag=DELETION,
#                 change_message=f"Deactivated {method_type.category} payment method: {method_type.name} ({display_ref})"
#             )


#             return Response(status=status.HTTP_204_NO_CONTENT)

#         except UserPaymentMethod.DoesNotExist:
#             return Response({'error': 'Payment method not found'}, status=status.HTTP_404_NOT_FOUND)
        
# class PaymentListCreateAPIView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def get(self, request):
#         user = request.user

#         # Get balance summary
#         balance_info = BalanceService.get_balance_summary(user, role='creator')

#         # Get active payment methods
#         methods = UserPaymentMethod.objects.filter(user=user, is_active=True)
#         methods_data = UserPaymentMethodSerializer(methods, many=True).data

#         # Get last withdrawal request
#         last_withdrawal = WithdrawalRequest.objects.filter(
#             user_payment_method__user=user,
#             status__in=[
#                 WithdrawalRequest.RequestStatus.APPROVED,
#                 WithdrawalRequest.RequestStatus.COMPLETED,
#                 WithdrawalRequest.RequestStatus.PENDING,
#             ]
#         ).order_by('-created_at').first()

#         last_transaction = None

#         def mask(value):
#             return '*' * (len(value) - 4) + value[-4:] if value and len(value) > 4 else value or "****"

#         if last_withdrawal:
#             method = last_withdrawal.user_payment_method
#             if method and method.payment_method_type:
#                 method_type = method.payment_method_type
#                 if method_type.category == 'bank':
#                     account_ending = mask(method.account_number)
#                 elif method_type.category == 'wallet':
#                     account_ending = mask(str(method.phone_number))
#                 else:
#                     account_ending = "****"

#                 last_transaction = {
#                     'amount': str(last_withdrawal.amount),
#                     'account_ending': account_ending,
#                     'method_type': method_type.category,  # e.g., 'bank', 'wallet'
#                     'method_display': method_type.name,   # e.g., 'Direct to Bank'
#                     'currency': 'ETB',
#                     'status': last_withdrawal.status,
#                     'created_at': last_withdrawal.created_at
#                 }

#         # Fetch transactions
#         transactions = Transaction.objects.filter(
#             user=user, 
#             sub_balance__in=['available', 'pending_withdrawals'], 
#             ).order_by('-timestamp')
#         transaction_data = [{
#             'transaction_type': tx.transaction_type,
#             'transaction_type_display': tx.get_transaction_type_display(),
#             'amount': str(tx.amount),
#             'note': tx.transaction_reference,
#             'created_at': tx.timestamp,
#         } for tx in transactions]

#         return Response({
#             'balance': {
#                 'available': str(balance_info.get('available', '0.00')),
#                 'locked': str(balance_info.get('escrow', '0.00')),
#                 'pending_balance': str(balance_info.get('escrow', '0.00')),
#             },
#             'payment_methods': methods_data,
#             'transaction': last_transaction,
#             'transactions': transaction_data
#         })

#     def post(self, request):
#         serializer = UserPaymentMethodSerializer(data=request.data, context={'request': request})
#         if serializer.is_valid():
#             payment_method = serializer.save()
#             user_methods = UserPaymentMethod.objects.filter(user=request.user, is_active=True)

#             if user_methods.count() == 1:
#                 payment_method.is_default = True
#                 payment_method.save()
#             elif payment_method.status == UserPaymentMethod.Status.VERIFIED:
#                 payment_method.set_as_default()
#             else:
#                 payment_method.is_default = False
#                 payment_method.save()

#             display_ref = payment_method.get_display_reference()

#             LogEntry.objects.log_action(
#                 user_id=request.user.id,
#                 content_type_id=ContentType.objects.get_for_model(UserPaymentMethod).pk,
#                 object_id=payment_method.pk,
#                 object_repr=f"{payment_method.payment_method_type.name} ({display_ref})",
#                 action_flag=ADDITION,
#                 change_message=f"Added {payment_method.payment_method_type.category} method"
#             )

#             return Response({
#                 'ok': True,
#                 'message': 'Payment method added successfully',
#                 'payment_method': UserPaymentMethodSerializer(payment_method).data
#             }, status=status.HTTP_201_CREATED)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class TransactionsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        transactions = Transaction.objects.filter(
            user=request.user,
            transaction_type__in=['withdraw', 'credit', 'debit'],
            sub_balance='available'
        ).select_related('balance', 'user').order_by('-timestamp')
        
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(transactions, request)
        serializer = TransactionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

class PaymentListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user

        # Get balance summary
        balance_info = BalanceService.get_balance_summary(user, role='creator')

        # Get active payment methods
        methods = UserPaymentMethod.objects.filter(user=user, is_active=True)
        methods_data = UserPaymentMethodSerializer(methods, many=True).data

        # Get last withdrawal request
        last_withdrawal = WithdrawalRequest.objects.filter(
            user_payment_method__user=user,
            status='completed'
        ).select_related('user_payment_method__payment_method_type').order_by('-completed_at').first()

        last_withdrawal_data = None
        if last_withdrawal:
            method = last_withdrawal.user_payment_method
            method_type = method.payment_method_type
            account_ending = (
                ('****' + method.account_number[-4:]) if method_type.category == 'bank' and method.account_number
                else ('****' + str(method.phone_number)[-4:]) if method_type.category == 'wallet' and method.phone_number
                else '****'
            )
            last_withdrawal_data = {
                'amount': str(last_withdrawal.amount),
                'account_ending': account_ending,
                'method_type': method_type.category,
                'method_display': method_type.name,
                'currency': 'ETB',
                'status': last_withdrawal.status,
                'created_at': last_withdrawal.created_at,
                'completed_at': last_withdrawal.completed_at,
                'reference': last_withdrawal.reference
            }

        # Get latest pending/approved withdrawal request
        latest_withdrawal_request = WithdrawalRequest.objects.filter(
            user_payment_method__user=user,
            status__in=['pending', 'approved']
        ).select_related('user_payment_method__payment_method_type').order_by('-created_at').first()

        latest_withdrawal_request_data = None
        if latest_withdrawal_request:
            method = latest_withdrawal_request.user_payment_method
            method_type = method.payment_method_type
            account_ending = (
                ('****' + method.account_number[-4:]) if method_type.category == 'bank' and method.account_number
                else ('****' + str(method.phone_number)[-4:]) if method_type.category == 'wallet' and method.phone_number
                else '****'
            )
            latest_withdrawal_request_data = {
                'amount': str(latest_withdrawal_request.amount),
                'account_ending': account_ending,
                'method_type': method_type.category,
                'method_display': method_type.name,
                'currency': 'ETB',
                'status': latest_withdrawal_request.status,
                'created_at': latest_withdrawal_request.created_at,
                'reference': latest_withdrawal_request.reference
            }

        # Fetch transactions
        transactions = Transaction.objects.filter(
            user=user,
            transaction_type__in=['withdraw', 'credit', 'debit'],
            sub_balance__in=['available', 'pending_withdrawals', ]
        ).select_related('balance', 'user').order_by('-timestamp')
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(transactions, request)
        transaction_data = TransactionSerializer(page, many=True).data
        return Response({
            'balance': {
                'available': str(balance_info.get('available', '0.00')),
                'escrow': str(balance_info.get('escrow', '0.00')),
                'pending_withdrawals': str(balance_info.get('pending_withdrawals', '0.00')),
                'total': str(balance_info.get('total', '0.00'))
            },
            'payment_methods': methods_data,
            'last_withdrawal': last_withdrawal_data,
            'latest_withdrawal_request': latest_withdrawal_request_data,
            'transactions': transaction_data,
            'pagination': {
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
                'count': paginator.page.paginator.count
            }
        })

    def post(self, request):
        serializer = UserPaymentMethodSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            payment_method = serializer.save()
            user_methods = UserPaymentMethod.objects.filter(user=request.user, is_active=True)

            if user_methods.count() == 1:
                payment_method.is_default = True
                payment_method.save()
            elif payment_method.status == UserPaymentMethod.Status.VERIFIED:
                payment_method.set_as_default()
            else:
                payment_method.is_default = False
                payment_method.save()

            display_ref = payment_method.get_display_reference()

            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(UserPaymentMethod).pk,
                object_id=payment_method.pk,
                object_repr=f"{payment_method.payment_method_type.name} ({display_ref})",
                action_flag=ADDITION,
                change_message=f"Added {payment_method.payment_method_type.category} method"
            )

            return Response({
                'ok': True,
                'message': 'Payment method added successfully',
                'payment_method': UserPaymentMethodSerializer(payment_method).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PaymentDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, method_id):
        try:
            payment_method = UserPaymentMethod.objects.get(id=method_id, user=request.user)
        except UserPaymentMethod.DoesNotExist:
            raise NotFound('Payment method not found.')

        serializer = UserPaymentMethodSerializer(
            payment_method, data=request.data, partial=True, context={'request': request}
        )

        if serializer.is_valid():
            updated = serializer.save()
            user_methods = UserPaymentMethod.objects.filter(user=request.user, is_active=True)

            # Allow making default if it's verified or the only method
            if request.data.get('is_default') is True:
                if updated.status == UserPaymentMethod.Status.VERIFIED:
                    updated.set_as_default()
                else:
                    return Response({
                        'is_default': ['Only verified methods can be set as default.']
                    }, status=status.HTTP_400_BAD_REQUEST)

            display_ref = updated.get_display_reference()

            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(UserPaymentMethod).pk,
                object_id=updated.pk,
                object_repr=f"{updated.payment_method_type.name} ({display_ref})",
                action_flag=CHANGE,
                change_message="Updated payment method"
            )

            return Response({
                'ok': True,
                'message': 'Payment method updated successfully',
                'payment_method': UserPaymentMethodSerializer(updated).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, method_id):
        if not method_id:
            return Response({'error': 'Method ID is required'}, status=400)

        try:
            method = UserPaymentMethod.objects.get(id=method_id, user=request.user)

            active_methods = UserPaymentMethod.objects.filter(user=request.user, is_active=True)

            if active_methods.count() == 1:
                return Response(
                    {'error': 'Cannot delete your only payment method'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Deactivate the method
            method.is_active = False
            method.is_default = False
            method.account_name = f"{method.account_name}--DELETE-{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            method.save()

            # ⚠️ If no default exists anymore, set the remaining one as default
            remaining_methods = UserPaymentMethod.objects.filter(user=request.user, is_active=True).exclude(id=method.id)

            if not remaining_methods.filter(is_default=True).exists():
                new_default = remaining_methods.first()
                if new_default:
                    new_default.is_default = True
                    new_default.save()

            # Logging
            method_type = method.payment_method_type
            display_ref = method.get_display_reference()

            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(UserPaymentMethod).pk,
                object_id=method.pk,
                object_repr=str(method),
                action_flag=DELETION,
                change_message=f"Deactivated {method_type.category} payment method: {method_type.name} ({display_ref})"
            )

            return Response(status=status.HTTP_204_NO_CONTENT)

        except UserPaymentMethod.DoesNotExist:
            return Response({'error': 'Payment method not found'}, status=status.HTTP_404_NOT_FOUND)
    
    
class WithdrawalAPIView(APIView):
    permission_classes = [IsCreatorUser, permissions.IsAuthenticated]

    def post(self, request):
        serializer = WithdrawalRequestSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            user = request.user
            amount = serializer.validated_data['amount']
            payment_method = serializer.validated_data['user_payment_method']
            payment_method_id = payment_method.id

            try:
                withdrawal = WithdrawalService.request_withdrawal(
                    user=user,
                    amount=amount,
                    user_payment_method_id=payment_method_id
                )

                balance_summary = BalanceService.get_balance_summary(user, role="creator")

                LogEntry.objects.log_action(
                    user_id=user.id,
                    content_type_id=ContentType.objects.get_for_model(WithdrawalRequest).pk,
                    object_id=withdrawal.pk,
                    object_repr=f"Withdrawal for {user.username} via {payment_method.payment_method_type.name} ({payment_method.account_name})",
                    action_flag=ADDITION,
                    change_message=f"Submitted withdrawal request of {withdrawal.amount} for payment method: {payment_method.payment_method_type.name}"
                )
                return Response({
                    'message': 'Withdrawal request submitted',
                    'new_available_balance': str(balance_summary['available']),
                    'locked_balance': str(balance_summary['escrow']),
                    'pending_withdrawals': str(balance_summary['pending_withdrawals']),
                    'withdrawal_id': withdrawal.id,
                    'reference': withdrawal.reference  # Include reference for frontend
                }, status=status.HTTP_201_CREATED)

            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ApproveAdPlacement(APIView):
    permission_classes = [IsCreatorUser, permissions.IsAuthenticated]

    def post(self, request, pk):
        # Fetch the ad placement object
        adplacement = get_object_or_404(AdPlacement, pk=pk)
        
        # Update the adplacement status to 'approved' and set it as active
        adplacement.status = 'approved'
        adplacement.is_active = True
        adplacement.save()
        
        # Log the approval action
        LogEntry.objects.log_action(
            user_id=request.user.id,
            content_type_id=ContentType.objects.get_for_model(AdPlacement).pk,
            object_id=adplacement.pk,
            object_repr=str(adplacement),
            action_flag=CHANGE, 
            change_message=f"Approved ad placement for {adplacement.ad.headline} on {adplacement.channel.title}"
        )
        
        # Send response
        return Response({
            "message": f"Ad Placement for {adplacement.ad.headline} on {adplacement.channel.title} approved successfully!",
            "adplacement": AdPlacementSerializer(adplacement).data
        }, status=status.HTTP_200_OK)

# Reject Ad Placement API
class RejectAdPlacement(APIView):
    permission_classes = [IsCreatorUser, permissions.IsAuthenticated]

    def post(self, request, pk):
        # Fetch the ad placement object
        adplacement = get_object_or_404(AdPlacement, pk=pk)

        # Reject the adplacement and update its status
        adplacement.status = 'rejected'
        adplacement.is_active = False
        adplacement.save()

        # Log the rejection action
        LogEntry.objects.log_action(
            user_id=request.user.id,
            content_type_id=ContentType.objects.get_for_model(AdPlacement).pk,
            object_id=adplacement.pk,
            object_repr=str(adplacement),
            action_flag=CHANGE, 
            change_message=f"Rejected ad placement for {adplacement.ad.headline} on {adplacement.channel.title}"
        )

        # Send response
        return Response({
            "message": f"Ad Placement for {adplacement.ad.headline} on {adplacement.channel.title} rejected.",
            "adplacement": AdPlacementSerializer(adplacement).data
        }, status=status.HTTP_200_OK)
        

class ActiveCategoryListAPIView(APIView):
    def get(self, request):
        categories = Category.objects.filter(is_active=True)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

class LanguageListAPIView(APIView):
    def get(self, request):
        languages = Language.objects.filter(is_active=True)
        serializer = LanguageSerializer(languages, many=True)
        return Response(serializer.data)
    


TRUSTED_DISPATCHER_HEADER = "X-Dispatched-By"
TRUSTED_DISPATCHER_VALUE = "local-scraper" 


def is_request_trusted(request):
    return request.headers.get(TRUSTED_DISPATCHER_HEADER) == TRUSTED_DISPATCHER_VALUE

class VerifiedChannelListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        if not is_request_trusted(request):
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        channels = CreatorChannel.objects.filter(status=CreatorChannel.ChannelStatus.VERIFIED).select_related('owner__telegram_profile')
        data = []

        for channel in channels:
            username = channel.channel_link.replace("https://t.me/", "").strip("/")
            
            try:
                tg_id = channel.owner.telegram_profile.tg_id
            except Exception as e:
                print(e)
                tg_id = None 

            data.append({
                "id": str(channel.id),
                "username": username,
                "owner": tg_id,
                "subscribers": channel.subscribers,
                "last_score_updated": channel.last_score_updated
            })

        return Response(data)


# class ChannelMLScoreBulkUpdateAPIView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def patch(self, request):
#         if not is_request_trusted(request):
#             return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

#         updates = request.data
#         if not isinstance(updates, list):
#             return Response({"error": "Expected a list of channel updates"}, status=400)

#         updated = []
#         failed = []

#         for item in updates:
#             username = item.get("username")
#             ml_score = item.get("ml_score")
#             pp_url = item.get("pp_url")  
#             subscribers = item.get("subscribers")  

#             if not username or ml_score is None:
#                 failed.append({"entry": item, "error": "Missing username or ml_score"})
#                 continue

#             channel_link = f"https://t.me/{username}"

#             try:
#                 channel = CreatorChannel.objects.get(channel_link__iexact=channel_link)
#                 previous_score = channel.ml_score or 0
#                 channel.ml_score = ml_score
#                 channel.last_score_updated = timezone.now()

#                 update_fields = ['ml_score', 'last_score_updated']
#                 if pp_url:
#                     channel.pp_url = pp_url
#                     update_fields.append('pp_url')
#                 if subscribers is not None:
#                     channel.subscribers = subscribers
#                     update_fields.append('subscribers')

#                 channel.save(update_fields=update_fields)

#                 # ─── Notify the Channel Owner ───
#                 if channel.owner:
#                     title = "Channel Performance Updated"
                    
#                     # Determine performance change
#                     diff = round(ml_score - previous_score, 2)

#                     # Set is_active based on the score change
#                     is_active_notification = True
#                     if abs(diff) < 0.2:  # Threshold for "insignificant" change
#                         is_active_notification = False
                    
#                     if previous_score is None or previous_score == 0:
#                         # First time update, always active
#                         trend = "for the first time"
#                         tone = "Your channel just received its first performance score."
#                         is_active_notification = True
#                     elif diff > 0.2:
#                         trend = "increased ↗"
#                         tone = "Great! Your channel's performance is improving."
#                     elif diff < -0.2:
#                         trend = "decreased ↘"
#                         tone = "Heads up! Your channel's performance has dropped."
#                     else:
#                         trend = "remained the same"
#                         tone = "Your performance score hasn't changed."
#                         is_active_notification = False # Set to false for insignificant changes
                    
#                     message = (
#                         f"Your channel \"{channel.title}\" has a new performance analysis.\n"
#                         f"Score {trend} from {previous_score:.2f} to {ml_score:.2f}. {tone}"
#                     )

#                     Notification.objects.create(
#                         user=channel.owner,
#                         title=title,
#                         message=message,
#                         type='Analytics Update',
#                         is_active=is_active_notification # Use the flag here
#                     )

                # updated.append({
                #     "channel_link": channel_link,
                #     "ml_score": ml_score,
                #     "pp_url": pp_url,
                #     "subscribers": subscribers
                # })
                
#             except CreatorChannel.DoesNotExist:
#                 failed.append({"channel_link": channel_link, "error": "Not found"})

#         return Response({"updated": updated, "failed": failed})
    

class ChannelMLScoreBulkUpdateAPIView(APIView):
    """
    Receives a bulk update of ML scores and analytics from the external script.
    Updates CreatorChannel's ML score and calculates estimated reputation metrics
    (views, min/max cost) based on the channel's fixed min_cpm.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        if not is_request_trusted(request):
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        updates = request.data
        if not isinstance(updates, list):
            return Response({"error": "Expected a list of channel updates"}, status=status.HTTP_400_BAD_REQUEST)

        updated = []
        failed = []

        for item in updates:
            # 2. Extract Data from Payload
            username = item.get("username")
            ml_score = item.get("ml_score")
            pp_url = item.get("pp_url")
            subscribers = item.get("subscribers")
            
            avg_views_per_post = item.get("avg_views_per_post")
            engagement_rate = item.get("engagement_rate")
            top_views_post = item.get("top_views_post")

            if not username or ml_score is None:
                failed.append({"entry": item, "error": "Missing username or ml_score"})
                continue

            channel_link = f"https://t.me/{username}"

            try:
        
                channel = CreatorChannel.objects.get(channel_link__iexact=channel_link)
                previous_score = channel.ml_score or 0
                
                channel.ml_score = ml_score
                channel.last_score_updated = timezone.now()

                update_fields = ['ml_score', 'last_score_updated']
                if pp_url:
                    channel.pp_url = pp_url
                    update_fields.append('pp_url')
                if subscribers is not None:
                    channel.subscribers = subscribers
                    update_fields.append('subscribers')

                channel.save(update_fields=update_fields)

                
                reputation, created = CreatorReputation.objects.get_or_create(
                    creator_channel=channel
                )
                
                estimated_cost_min = Decimal('0.00')
                estimated_cost_max = Decimal('0.00')
                
                try:
                    FIXED_CPM = channel.min_cpm if channel.min_cpm is not None else Decimal('0.0')
                    if not isinstance(FIXED_CPM, Decimal):
                        FIXED_CPM = Decimal(str(FIXED_CPM))
                except InvalidOperation:
                    FIXED_CPM = Decimal('0.0')

            
                if FIXED_CPM > Decimal('0.00'):
                    
                    min_views = int(avg_views_per_post or 0)
                    max_views = int(top_views_post or 0)
                    
                    # Cost = (Views / 1000) * CPM
                    views_ratio_min = Decimal(min_views) / Decimal(1000)
                    estimated_cost_min = views_ratio_min * FIXED_CPM
                    
                    views_ratio_max = Decimal(max_views) / Decimal(1000)
                    estimated_cost_max = views_ratio_max * FIXED_CPM

                
                if engagement_rate is not None:
                    try:
                        reputation.avg_engagement_rate = round(float(engagement_rate), 2)
                    except (TypeError, ValueError):
                        reputation.avg_engagement_rate = 0.0 
                
                reputation.estimated_views_avg = int(avg_views_per_post or 0)
                reputation.estimated_views_max = int(top_views_post or 0)
                
                # Assign and quantize Decimal values
                reputation.estimated_cost_min = estimated_cost_min.quantize(Decimal('0.01'))
                reputation.estimated_cost_max = estimated_cost_max.quantize(Decimal('0.01'))
                reputation.last_reviewed = timezone.now()
                
                reputation.save(
                    update_fields=[
                        'avg_engagement_rate', 
                        'estimated_views_avg', 
                        'estimated_views_max',
                        'estimated_cost_min',
                        'estimated_cost_max',
                        'last_reviewed',
                        'updated_at',
                    ]
                )
                
                if channel.owner:
                    title = "Channel Performance Updated"
                    diff = round(ml_score - previous_score, 2)

                    is_active_notification = True
                    
                    if previous_score is None or previous_score == 0:
                        trend = "for the first time"
                        tone = "Your channel just received its first performance score."
                        is_active_notification = True
                    elif diff > 0.2:
                        trend = "increased ↗"
                        tone = "Great! Your channel's performance is improving."
                    elif diff < -0.2:
                        trend = "decreased ↘"
                        tone = "Heads up! Your channel's performance has dropped."
                    else:
                        trend = "remained the same"
                        tone = "Your performance score hasn't changed."
                        is_active_notification = False
                        
                    message = (
                        # Improved initial flow
                        f"Your channel \"{channel.title}\" has a new performance analysis, resulting in a score update.\n"
                        
                        # Existing score summary
                        f"Score {trend} from {previous_score:.2f} to {ml_score:.2f}. {tone}\n\n"
                        
                        f"💰 Estimated Value Per Single Ad: ETB{reputation.estimated_cost_min:.2f} - ETB{reputation.estimated_cost_max:.2f}\n"
                        f"This is the estimated value for just one ad post per uv. **The more high-quality ads you run with us, the higher your total revenue potential!** Keep delivering great content to maximize your earnings on our platform."
                    )
                    
                    # message = (
                    #     # Achievement & Partnership Focus
                    #     f"🌟 **Performance Review Ready!** Your channel, \"{channel.title}\", has received an updated performance analysis on our platform.\n"
                        
                    #     # Feedback & Encouragement (Keep the score update but wrap it in positive language)
                    #     f"Your Channel Quality Score has {trend} from **{previous_score:.2f} to {ml_score:.2f}**! {tone}\n"
                        
                    #     # Value & Potential (Clear Earning Potential)
                    #     f"This improved performance significantly raises your value to our advertisers. Here is your current earning potential:\n"
                        
                    #     f"💰 **Estimated Value Per Single Ad Slot:** ETB{reputation.estimated_cost_min:.2f} - ETB{reputation.estimated_cost_max:.2f}\n\n"
                        
                    #     # Call to Action & Shared Goal
                    #     f"This is the estimated value for just one post. **The more high-quality ads you run with us, the higher your total revenue potential!** Keep delivering great content to maximize your earnings on our platform."
                    # )
                    Notification.objects.create(
                        user=channel.owner, 
                        title=title,
                        message=message,
                        type='Analytics Update',
                        is_active=is_active_notification
                    )

                updated.append({
                    "channel_link": channel_link,
                    "ml_score": ml_score,
                    "pp_url": pp_url,
                    "subscribers": subscribers
                })
                
            except CreatorChannel.DoesNotExist:
                failed.append({"channel_link": channel_link, "error": "Not found"})
               
            except Exception as e:
                failed.append({"channel_link": channel_link, "error": f"Internal error: {str(e)}"})
         

        return Response({"updated": updated, "failed": failed})