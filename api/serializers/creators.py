from django.conf import settings
from django.db.models import Sum, Count, Q, F, DecimalField
from decimal import Decimal
from rest_framework import serializers
from django.contrib.admin.models import LogEntry
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.utils.security import generate_activation_code
from creators.models import (
    CreatorChannel,
)
from core.models import (
    Category,
    Language,
    AdPlacement,
    AdPerformance,
)
from payments.models import (
    PaymentMethodType,
    UserPaymentMethod, 
    WithdrawalRequest, 
    Transaction
)
from api.serializers.notifications import NotificationSerializer
from django.contrib.auth import get_user_model
User = get_user_model()

class AdPerformanceSerializer(serializers.ModelSerializer):
    ctr = serializers.SerializerMethodField()
    cpm = serializers.SerializerMethodField()
    engagement_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = AdPerformance
        fields = [
            'date', 'impressions', 'clicks', 'conversions',
            'cost', 'total_reactions', 'total_replies',
            'views', 'forwards', 'ctr', 'cpm', 'engagement_rate'
        ]
    
    def get_ctr(self, obj):
        return (obj.clicks / obj.impressions * 100) if obj.impressions else 0.0
    
    def get_cpm(self, obj):
        return (obj.cost / obj.impressions * 1000) if obj.impressions else 0.0
    
    def get_engagement_rate(self, obj):
        total = obj.total_reactions + obj.total_replies
        return (total / obj.impressions * 100) if obj.impressions else 0.0

class AdPlacementSerializer(serializers.ModelSerializer):
    ad_headline = serializers.CharField(source='ad.headline')
    ad_brand_name = serializers.CharField(source='ad.brand_name')
    ad_img_url = serializers.CharField(source='ad.img_url')
    channel_title = serializers.CharField(source='channel.title')
    status_display = serializers.CharField(source='get_status_display')
    winning_bid_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    preference_score = serializers.FloatField()
    performance = AdPerformanceSerializer(many=True, read_only=True)


    class Meta:
        model = AdPlacement
        fields = [
            'id', 'ad_headline', 'ad_brand_name', 'ad_img_url',
            'channel_title', 'placed_at', 'status', 'status_display',
            'winning_bid_price', 'preference_score', 'content_platform_id', 'performance',
        ]

class ChannelSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display')
    region_display = serializers.CharField(source='get_region_display')
    language = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    engagement_rate = serializers.SerializerMethodField()
    ad_placements = AdPlacementSerializer(many=True, read_only=True)
    class Meta:
        model = CreatorChannel
        fields = [
            'id', 'title', 'channel_link', 'subscribers',
            'status', 'status_display', 'pp_url', 'language',
            'category', 'stats', 'engagement_rate', 'region', 'region_display',
            'timezone', 'min_cpm', 'repost_preference',
            'repost_preference_frequency', 'auto_publish',
            'ad_placements', 'created_at', 'updated_at'
        ]

    def get_engagement_rate(self, obj):
        return obj.ml_score

    def get_language(self, obj):
        return [lang.name for lang in obj.language.all()]

    def get_category(self, obj):
        return [cat.name for cat in obj.category.all()]

    def get_stats(self, obj):
        CREATOR_SHARE_MULTIPLIER = Decimal('1') - (Decimal(settings.PLATFORM_FEE) / Decimal('100'))
        performance = AdPerformance.objects.filter(
            ad_placement__channel=obj
        ).aggregate(
            total_impressions=Sum('impressions'),
            total_earnings=Sum(F('cost') * CREATOR_SHARE_MULTIPLIER, output_field=DecimalField())
        )
        return {
            'active_ads': obj.ad_placements.filter(
                status__in=['running', 'approved']
            ).count(),
            'total_impressions': performance['total_impressions'] or 0,
            'total_earnings': round(float(performance['total_earnings'] or 0), 2),
            'engagement_rate': obj.ml_score
        }
        
    
class ChannelUpdateSerializer(serializers.ModelSerializer):
    language = serializers.PrimaryKeyRelatedField(queryset=Language.objects.all(), many=True, required=False)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), many=True, required=False)

    class Meta:
        model = CreatorChannel
        exclude = ['activation_code', 'status', 'owner', 'created_at', 'updated_at', 'channel_id']

    def update(self, instance, validated_data):
        language_data = validated_data.pop('language', None)
        category_data = validated_data.pop('category', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if language_data is not None:
            instance.language.set(language_data)
        if category_data is not None:
            instance.category.set(category_data)

        return instance
    
class PaymentMethodTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethodType
        fields = ['id', 'name', 'short_name', 'category', 'logo']

# class UserPaymentMethodSerializer(serializers.ModelSerializer):
#     phone_number = serializers.CharField(required=False, allow_blank=True)
#     account_number = serializers.CharField(required=False, allow_blank=True)
#     payment_method_type = serializers.PrimaryKeyRelatedField(
#         queryset=PaymentMethodType.objects.filter(is_active=True)
#     )
#     payment_method_type_details = PaymentMethodTypeSerializer(
#         source='payment_method_type', read_only=True
#     )

#     class Meta:
#         model = UserPaymentMethod
#         fields = [
#             'id',
#             'payment_method_type',
#             'payment_method_type_details',
#             'account_name',
#             'account_number',
#             'phone_number',
#             'status',
#             'is_default',
#         ]
#         read_only_fields = ['status']

#     def validate(self, data):
#         payment_method = data.get('payment_method_type')
#         request = self.context.get('request')
#         user = request.user if request else None

#         if not payment_method:
#             raise serializers.ValidationError({'payment_method_type': 'This field is required.'})

#         category = payment_method.category

#         # Validate required fields
#         if category == PaymentMethodType.MethodCategory.BANK:
#             if not data.get('account_number'):
#                 raise serializers.ValidationError({'account_number': 'Bank account number is required.'})
#         elif category == PaymentMethodType.MethodCategory.WALLET:
#             if not data.get('phone_number'):
#                 raise serializers.ValidationError({'phone_number': 'Phone number is required.'})

#         # Match account name to user name
#         if user and 'account_name' in data:
#             user_full_name = f"{user.first_name} {user.last_name}".strip().lower()
#             account_name = data['account_name'].strip().lower()
#             if user_full_name != account_name:
#                 raise serializers.ValidationError({
#                     'account_name': 'Account name must match your full name on file.'
#                 })

#         # Check uniqueness
#         if user:
#             existing = UserPaymentMethod.objects.filter(
#                 user=user,
#                 payment_method_type=payment_method,
#                 account_name=data.get('account_name'),
#                 is_active=True
#             )
#             if existing.exists():
#                 raise serializers.ValidationError({
#                     'account_name': 'This payment method already exists for your account.'
#                 })

#         return data

#     def create(self, validated_data):
#         user = self.context['request'].user
#         return UserPaymentMethod.objects.create(user=user, **validated_data)

#     def to_representation(self, instance):
#         """
#         Mask account_number and phone_number in API output.
#         """
#         data = super().to_representation(instance)

#         def mask(value):
#             if not value:
#                 return value
#             return '*' * (len(value) - 4) + value[-4:]

#         data['account_number'] = mask(data.get('account_number'))
#         data['phone_number'] = mask(data.get('phone_number'))

#         return data

   


class UserPaymentMethodSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(required=False, allow_blank=True)
    account_number = serializers.CharField(required=False, allow_blank=True)
    payment_method_type = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethodType.objects.filter(is_active=True)
    )
    payment_method_type_details = PaymentMethodTypeSerializer(
        source='payment_method_type', read_only=True
    )

    class Meta:
        model = UserPaymentMethod
        fields = [
            'id',
            'payment_method_type',
            'payment_method_type_details',
            'account_name',
            'account_number',
            'phone_number',
            'status',
            'is_default',
        ]
        read_only_fields = ['status']

    def validate(self, data):
        request = self.context.get('request')
        user = request.user if request else None
        method_type = data.get('payment_method_type') or getattr(self.instance, 'payment_method_type', None)
        category = method_type.category if method_type else None

        if self.instance and category == PaymentMethodType.MethodCategory.BANK:
            if 'account_number' in data and not data.get('account_number'):
                raise serializers.ValidationError({'account_number': 'Bank account number is required.'})
        elif category == PaymentMethodType.MethodCategory.BANK and not data.get('account_number'):
            raise serializers.ValidationError({'account_number': 'Bank account number is required.'})

        if self.instance and category == PaymentMethodType.MethodCategory.WALLET:
            # If updating and phone_number is missing in data, keep original
            if 'phone_number' in data and not data.get('phone_number'):
                raise serializers.ValidationError({'phone_number': 'Phone number is required.'})
        elif category == PaymentMethodType.MethodCategory.WALLET and not data.get('phone_number'):
            raise serializers.ValidationError({'phone_number': 'Phone number is required.'})

        if user and 'account_name' in data:
            full_name = f"{user.first_name} {user.last_name}".strip().lower()
            if full_name != data['account_name'].strip().lower():
                raise serializers.ValidationError({
                    'account_name': 'Account name must match your full name on file.'
                })

        if user and method_type and 'account_name' in data:
            existing = UserPaymentMethod.objects.filter(
                user=user,
                payment_method_type=method_type,
                account_name=data['account_name'],
                is_active=True
            )
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            if existing.exists():
                raise serializers.ValidationError({
                    'account_name': 'This payment method already exists for your account.'
                })

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        return UserPaymentMethod.objects.create(user=user, **validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        def mask(value):
            return '*' * (len(value) - 4) + value[-4:] if value else value

        data['account_number'] = mask(data.get('account_number'))
        data['phone_number'] = mask(data.get('phone_number'))

        return data
      
class DashboardSerializer(serializers.Serializer):
    top_channels = ChannelSerializer(many=True)
    active_ad_placements = AdPlacementSerializer(many=True)
    payment_methods = UserPaymentMethodSerializer(many=True)
    earning = serializers.DictField()
    chart_data = serializers.ListField(child=serializers.FloatField())
    week_labels = serializers.ListField(child=serializers.CharField())
    week_ranges = serializers.ListField(child=serializers.CharField())
    notifications = NotificationSerializer(many=True)
    unread_count = serializers.IntegerField()
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['activity_logs'] = [
            {
                'change_message': log.change_message,
                'action_flag_display': log.get_action_flag_display(),
                'timestamp': log.action_time.strftime('%Y-%m-%d %H:%M:%S')
            }
            for log in instance['activity_logs']
        ]
        return ret

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'code', 'name']

class ChannelCreateSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    language = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Language.objects.all()
    )
    category = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.filter(is_active=True)
    )

    class Meta:
        model = CreatorChannel
        fields = [
            'owner', 'channel_link', 'language', 'category', 'min_cpm',
            'timezone', 'region', 'repost_preference', 'repost_preference_frequency',
            'auto_publish', 'pp_url'
        ]
        extra_kwargs = {
            'timezone': {'required': False},
            'region': {'required': False},
            'repost_preference': {'required': False},
            'repost_preference_frequency': {'required': False},
            'auto_publish': {'required': False},
            'pp_url': {'required': False},
        }

    def validate_category(self, value):
        if not value:
            raise serializers.ValidationError("At least one category is required.")
        if len(value) > 3:
            raise serializers.ValidationError("You can only select up to 3 categories.")
        return value

    def validate_language(self, value):
        if not value:
            raise serializers.ValidationError("At least one language is required.")
        if len(value) > 3:
            raise serializers.ValidationError("You can only select up to 3 languages.")
        return value

    def validate_channel_link(self, value):
        if not value.startswith('https://t.me/') or len(value) < 20:
            raise serializers.ValidationError("Enter a valid Telegram channel link (e.g., https://t.me/yourchannel).")
        return value

    def validate_min_cpm(self, value):
        if value <= 0:
            raise serializers.ValidationError("Minimum CPM must be a positive number.")
        return value
    
    def validate(self, data):
        user = self.context['request'].user

        # Enforce channel limit
        channel_count = CreatorChannel.objects.filter(owner=user).exclude(status='deleted').count()
        if channel_count >= 3:
            raise serializers.ValidationError("You can only register up to 3 channels.")

        return data

    def create(self, validated_data):
        request = self.context['request']
        user = request.user

        languages = validated_data.pop('language', [])
        categories = validated_data.pop('category', [])
        validated_data.pop('owner', None)

        activation_code = generate_activation_code(validated_data['channel_link'].replace('https://t.me/', ''), user.id)

        channel = CreatorChannel.objects.create(
            **validated_data,
            owner=user,
            status='pending',
            activation_code=activation_code,
            is_active=True
        )

        channel.language.set(languages)
        channel.category.set(categories)

        return channel
    
class ChannelVerificationSerializer(serializers.Serializer):
    activation_code = serializers.CharField()
    channel_id = serializers.CharField()
    title = serializers.CharField(required=False, allow_blank=True)
    subscribers = serializers.IntegerField(min_value=0, required=False)
         
class WithdrawalRequestSerializer(serializers.ModelSerializer):
    user_payment_method = serializers.UUIDField(write_only=True)

    class Meta:
        model = WithdrawalRequest
        fields = ['user_payment_method', 'amount']
        read_only_fields = ['status']

    def validate_user_payment_method(self, value):
        try:
            payment_method = UserPaymentMethod.objects.get(id=value, user=self.context['request'].user)
            if payment_method.status != 'verified':
                raise serializers.ValidationError("Payment method is not verified")
            return payment_method
        except UserPaymentMethod.DoesNotExist:
            raise serializers.ValidationError("Invalid payment method ID")
        except ValueError:
            raise serializers.ValidationError("Invalid UUID format")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value

    def to_internal_value(self, data):
        # Map user_payment_method_id to user_payment_method if provided
        if 'user_payment_method_id' in data and 'user_payment_method' not in data:
            data = data.copy()
            data['user_payment_method'] = data.pop('user_payment_method_id')
        return super().to_internal_value(data)
        


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'username', 'first_name', 'last_name',
            'email', 'user_type', 'address', 'email_verified',
            'phone_verified', 'last_seen', 'display_name'
        ]
        read_only_fields = ['id', 'phone_number', 'user_type', 'email_verified', 'phone_verified', 'last_seen', 'display_name']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'address']
        

class ChannelEngagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorChannel
        fields = ['username', 'owner', 'engagement_score', 'last_score_updated', 'subscribers']