from rest_framework import serializers
from payments.models import Transaction, WithdrawalRequest

class TransactionSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='transaction_type')
    display_type = serializers.SerializerMethodField()
    icon_class = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source='timestamp')
    reference = serializers.CharField(source='transaction_reference')
    sub_balance = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=True)
    after_balance = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=True)
    balance_detail = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'type', 'display_type', 'icon_class', 'date', 'reference',
            'amount', 'sub_balance', 'after_balance', 'balance_detail'
        ]

    def get_display_type(self, obj):
        if obj.transaction_type == 'withdraw':
            # Check if there's a corresponding WithdrawalRequest
            withdrawal = WithdrawalRequest.objects.filter(
                reference=obj.transaction_reference,
                user_payment_method__user=obj.user
            ).first()
            if withdrawal and withdrawal.status == 'pending':
                return 'Withdrawal Request'
            return 'Withdrawal'
        elif obj.transaction_type == 'credit':
            return 'Credit'
        elif obj.transaction_type == 'debit':
            return 'Debit'
        return obj.get_transaction_type_display()

    def get_icon_class(self, obj):
        icon_map = {
            'withdraw': 'fas fa-arrow-up text-danger',
            'credit': 'fas fa-plus text-success',
        }
        return icon_map.get(obj.transaction_type, 'fas fa-question text-muted')

    def get_balance_detail(self, obj):
        if obj.transaction_type == 'withdraw':
            withdrawal = WithdrawalRequest.objects.filter(
                reference=obj.transaction_reference,
                user_payment_method__user=obj.user
            ).first()
            if withdrawal:
                method = withdrawal.user_payment_method
                method_type = method.payment_method_type
                account_ending = (
                    ('****' + method.account_number[-4:]) if method_type.category == 'bank' and method.account_number
                    else ('****' + str(method.phone_number)[-4:]) if method_type.category == 'wallet' and method.phone_number
                    else '****'
                )
                return f"{method_type.name} ({account_ending})"
        elif obj.transaction_type == 'credit':
            return f"{obj.user}"
        return ''