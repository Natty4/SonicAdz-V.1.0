from decimal import Decimal
from django.db.models import Sum
from payments.models import Balance, Escrow, WithdrawalRequest, Transaction

class BalanceService:
    @staticmethod
    def get_balance_summary(user, limit=20, role: str = "creator"):
        """
        Returns a structured balance summary based on the user's role.
        Roles:
        - "creator": returns available, locked, and pending withdrawals
        - "advertiser": returns available, locked, pending escrow, total spent, and recent transactions
        """
        balance, _ = Balance.objects.get_or_create(user=user, type=user.user_type)
        summary = {
            'available': balance.available,
            'escrow': balance.escrow,
            'pending_withdrawals': Decimal('0.00'),
            'pending_escrow': Decimal('0.00'),
        }
        if role == "creator":
            summary['pending_withdrawals'] = WithdrawalRequest.objects.filter(
                user_payment_method__user=user,
                status=WithdrawalRequest.RequestStatus.PENDING
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        elif role == "advertiser":
            summary['pending_escrow'] = Escrow.objects.filter(
                advertiser=user,
                status=Escrow.EscrowStatus.PENDING
            ).aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0.00')
            summary['total_spent'] = Transaction.objects.filter(
                user=user,
                transaction_type='spend'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            summary['transactions'] = list(
                Transaction.objects.filter(
                    user=user, 
                    sub_balance__in=['available', 'pending_withdrawals', 'escrow'], 
                    ).order_by('-timestamp')[:limit]
            )
        else:
            raise ValueError("Invalid role passed to get_balance_summary. Must be 'creator' or 'advertiser'.")
        return summary

























































# from decimal import Decimal
# from django.db.models import Sum
# from payments.models import Balance, Escrow, WithdrawalRequest, Transaction


# class BalanceService:
#     @staticmethod
#     def get_balance_summary(user, limit=20, role: str = "creator"):
#         """
#         Returns a structured balance summary based on the user's role.

#         Roles:
#         - "creator": returns available, locked, and pending withdrawals
#         - "advertiser": returns available, locked, pending escrow, total spent, and recent transactions
#         """

#         balance, _ = Balance.objects.get_or_create(user=user)

#         summary = {
#             'available': balance.available,
#             'locked': balance.locked,
#             'pending_withdrawals': Decimal('0.00'),
#             'pending_escrow': Decimal('0.00'),
#         }

#         if role == "creator":
#             summary['pending_withdrawals'] = WithdrawalRequest.objects.filter(
#                 user_payment_method__user=user,
#                 status=WithdrawalRequest.RequestStatus.PENDING
#             ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

#         elif role == "advertiser":
#             summary['pending_escrow'] = Escrow.objects.filter(
#                 advertiser=user,
#                 status=Escrow.EscrowStatus.PENDING
#             ).aggregate(total=Sum('remaining_amount'))['total'] or Decimal('0.00')

#             summary['total_spent'] = Transaction.objects.filter(
#                 user=user,
#                 transaction_type='spend'
#             ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

#             summary['transactions'] = list(
#                 Transaction.objects.filter(user=user, transaction_type__in=['deposit', 'escrow_refund', 'escrow_lock', 'withdrawal']).order_by('-timestamp')[:limit]
#             )

#         else:
#             raise ValueError("Invalid role passed to get_balance_summary. Must be 'creator' or 'advertiser'.")

#         return summary