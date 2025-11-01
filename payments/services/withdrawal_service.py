import uuid
from decimal import Decimal
from django.utils import timezone
from django.db import transaction as db_transaction
from payments.models import (
    Balance, 
    WithdrawalRequest, 
    UserPaymentMethod, 
    AuditLog, 
    Transaction
)
from payments.utils import generate_transaction_reference

class WithdrawalService:
    @staticmethod
    def request_withdrawal(user, amount, user_payment_method_id, reference=None):
        with db_transaction.atomic():
            balance = Balance.objects.select_for_update().get(user=user, type=user.user_type)
            if amount > balance.available:
                raise ValueError("Insufficient available balance")
            user_payment_method = UserPaymentMethod.objects.get(id=user_payment_method_id, user=user)
            if user_payment_method.status != 'verified':
                raise ValueError("Payment method not verified")
            ref = reference or generate_transaction_reference('WDR')
            # Move amount to pending_withdrawals
            avail_after = balance.available - amount
            pending_after = balance.pending_withdrawals + amount
            balance.available = avail_after
            balance.pending_withdrawals = pending_after
            balance.save()
            # Create transaction (for Withdrawal Request, not shown in frontend due to sub_balance)
            Transaction.objects.create(
                user=user,
                balance=balance,
                transaction_type='withdraw',
                amount=amount,
                sub_balance='pending_withdrawals',
                after_balance=pending_after,
                transaction_reference=ref
            )
            # Create withdrawal request
            withdrawal_request = WithdrawalRequest.objects.create(
                user_payment_method=user_payment_method,
                amount=amount,
                status='pending',
                reference=ref
            )
            AuditLog.objects.create(
                user=user,
                action_type="withdrawal_request_created",
                target_type="WithdrawalRequest",
                target_id=str(withdrawal_request.id),
                description=f"User requested withdrawal of {amount}",
            )
            return withdrawal_request

    @staticmethod
    def approve_withdrawal(withdrawal_request_id, admin_user):
        with db_transaction.atomic():
            withdrawal_request = WithdrawalRequest.objects.select_for_update().get(id=withdrawal_request_id)
            if withdrawal_request.status != 'pending':
                raise ValueError("Withdrawal request is not pending")
            balance = Balance.objects.select_for_update().get(user=withdrawal_request.user_payment_method.user)
            if withdrawal_request.amount > balance.pending_withdrawals:
                raise ValueError("Insufficient pending withdrawals balance")
            # Update balance: reduce pending_withdrawals
            pending_withdrawals_after = balance.pending_withdrawals - withdrawal_request.amount
            balance.pending_withdrawals = pending_withdrawals_after
            balance.save()
            # Update withdrawal request
            withdrawal_request.status = 'approved'
            withdrawal_request.approved_at = timezone.now()
            withdrawal_request.save()
            AuditLog.objects.create(
                user=admin_user,
                action_type="withdrawal_request_approved",
                target_type="WithdrawalRequest",
                target_id=str(withdrawal_request.id),
                description=f"Admin approved withdrawal of {withdrawal_request.amount}",
            )
            return withdrawal_request

    @staticmethod
    def reject_withdrawal(withdrawal_request_id, admin_user):
        with db_transaction.atomic():
            withdrawal_request = WithdrawalRequest.objects.select_for_update().get(id=withdrawal_request_id)
            if withdrawal_request.status != 'pending':
                raise ValueError("Withdrawal request is not pending")
            balance = Balance.objects.select_for_update().get(user=withdrawal_request.user_payment_method.user)
            if withdrawal_request.amount > balance.pending_withdrawals:
                raise ValueError("Insufficient pending withdrawals balance")
            ref = generate_transaction_reference('REJ')
            # Move amount back to available
            pending_withdrawals_after = balance.pending_withdrawals - withdrawal_request.amount
            avail_after = balance.available + withdrawal_request.amount
            balance.pending_withdrawals = pending_withdrawals_after
            balance.available = avail_after
            balance.save()
            # Create transactions
            Transaction.objects.create(
                user=withdrawal_request.user_payment_method.user,
                balance=balance,
                transaction_type='debit',
                amount=withdrawal_request.amount,
                sub_balance='pending_withdrawals',
                after_balance=pending_withdrawals_after,
                transaction_reference=f'{ref}-DEB'
            )
            Transaction.objects.create(
                user=withdrawal_request.user_payment_method.user,
                balance=balance,
                transaction_type='credit',
                amount=withdrawal_request.amount,
                sub_balance='available',
                after_balance=avail_after,
                transaction_reference=f'{ref}-CRE'
            )
            withdrawal_request.status = 'rejected'
            withdrawal_request.save()
            AuditLog.objects.create(
                user=admin_user,
                action_type='withdrawal_request_rejected',
                target_type="WithdrawalRequest",
                target_id=str(withdrawal_request.id),
                description=f"Admin rejected withdrawal of {withdrawal_request.amount}",
            )
            return withdrawal_request

    @staticmethod
    def complete_withdrawal(withdrawal_request_id, admin_user):
        with db_transaction.atomic():
            withdrawal_request = WithdrawalRequest.objects.select_for_update().get(id=withdrawal_request_id)
            if withdrawal_request.status != 'approved':
                raise ValueError("Withdrawal request is not approved")
            balance = Balance.objects.select_for_update().get(user=withdrawal_request.user_payment_method.user)
            
            withdrawal_request.status = 'completed'
            withdrawal_request.completed_at = timezone.now()
            withdrawal_request.save()
            AuditLog.objects.create(
                user=admin_user,
                action_type="withdrawal_request_completed",
                target_type="WithdrawalRequest",
                target_id=str(withdrawal_request.id),
                description=f"Admin completed withdrawal of {withdrawal_request.amount}",
            )
            return withdrawal_request









































# import uuid
# from decimal import Decimal
# from django.utils import timezone
# from django.db import transaction as db_transaction
# from payments.models import (
#     Balance, 
#     WithdrawalRequest, 
#     UserPaymentMethod,
#     AuditLog,
# )

# class WithdrawalService:
#     @staticmethod
#     @db_transaction.atomic
#     def request_withdrawal(user, user_payment_method_id, amount: Decimal):
#         """User requests a withdrawal."""

#         if amount <= 0:
#             raise ValueError("Withdrawal amount must be positive")

#         try:
#             balance = Balance.objects.select_for_update().get(user=user)
#         except Balance.DoesNotExist:
#             raise ValueError("User balance does not exist")

#         if amount > balance.available:
#             raise ValueError("Insufficient available balance")

#         try:
#             payment_method = UserPaymentMethod.objects.get(id=user_payment_method_id, user=user)
#         except UserPaymentMethod.DoesNotExist:
#             raise ValueError("Invalid payment method")

#         # 1. Lock the balance
#         balance.available -= amount
#         # balance.locked += amount
#         balance.save()

#         # 2. Create withdrawal request
#         withdrawal_request = WithdrawalRequest.objects.create(
#             user_payment_method=payment_method,
#             amount=amount,
#             status=WithdrawalRequest.RequestStatus.PENDING,
#         )

#         # 3. Audit the action
#         AuditLog.objects.create(
#             user=user,
#             action_type="withdrawal_request_created",
#             target_type="WithdrawalRequest",
#             target_id=str(withdrawal_request.id),
#             description=f"User requested withdrawal of {amount}",
#         )

#         return withdrawal_request

#     @staticmethod
#     @db_transaction.atomic
#     def approve_withdrawal(withdrawal_request_id, admin_user):
#         """Approve a withdrawal request and deduct balance."""

#         try:
#             withdrawal_request = WithdrawalRequest.objects.select_for_update().get(id=withdrawal_request_id)
#         except WithdrawalRequest.DoesNotExist:
#             raise ValueError("Withdrawal request not found")

#         if withdrawal_request.status != WithdrawalRequest.RequestStatus.PENDING:
#             raise ValueError("Withdrawal request is not pending")

#         balance = withdrawal_request.user_payment_method.user.balance

#         if withdrawal_request.amount > balance.available:
#             raise ValueError("Insufficient available balance for withdrawal")

#         # Deduct available balance
#         balance.available -= withdrawal_request.amount
#         balance.save()

#         withdrawal_request.status = WithdrawalRequest.RequestStatus.APPROVED
#         withdrawal_request.approved_at = timezone.now()
#         withdrawal_request.save()

#         AuditLog.objects.create(
#             user=admin_user,
#             action_type="withdrawal_request_approved",
#             target_type="WithdrawalRequest",
#             target_id=str(withdrawal_request.id),
#             description=f"Admin approved withdrawal of {withdrawal_request.amount}",
#         )
#         return withdrawal_request

#     @staticmethod
#     @db_transaction.atomic
#     def complete_withdrawal(withdrawal_request_id, admin_user):
#         """Mark withdrawal as completed (after payout processed)."""

#         try:
#             withdrawal_request = WithdrawalRequest.objects.select_for_update().get(id=withdrawal_request_id)
#         except WithdrawalRequest.DoesNotExist:
#             raise ValueError("Withdrawal request not found")

#         if withdrawal_request.status != WithdrawalRequest.RequestStatus.APPROVED:
#             raise ValueError("Withdrawal request is not approved")

#         withdrawal_request.status = WithdrawalRequest.RequestStatus.COMPLETED
#         withdrawal_request.completed_at = timezone.now()
#         withdrawal_request.save()

#         AuditLog.objects.create(
#             user=admin_user,
#             action_type="withdrawal_request_completed",
#             target_type="WithdrawalRequest",
#             target_id=str(withdrawal_request.id),
#             description=f"Admin completed withdrawal of {withdrawal_request.amount}",
#         )
#         return withdrawal_request