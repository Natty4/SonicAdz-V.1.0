import uuid
from decimal import Decimal
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone
from payments.models import BalanceType, Balance, Transaction, Escrow, AuditLog
from payments.utils import generate_transaction_reference, get_creator_share

class PaymentAuditService:
    @staticmethod
    def audit(user, action_type, amount, target_type='payment', target_id=None):
        AuditLog.objects.create(
            user=user,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id or str(uuid.uuid4()),
            description=f'{action_type} of {amount}',
            timestamp=timezone.now()
        )

class WalletService:
    @staticmethod
    def deposit(user, amount, reference=None):
        with db_transaction.atomic():
            balance = Balance.objects.select_for_update().get(user=user)
            ref = reference or generate_transaction_reference('DEP')
            avail_after = balance.available + amount
            balance.available = avail_after
            balance.save()
            Transaction.objects.create(
                user=user,
                balance=balance,
                transaction_type='deposit',
                amount=amount,
                sub_balance='available',
                after_balance=avail_after,
                transaction_reference=ref
            )
            PaymentAuditService.audit(user, 'deposit', amount)
            return ref

    @staticmethod
    def withdraw(user, amount, reference=None):
        with db_transaction.atomic():
            balance = Balance.objects.select_for_update().get(user=user)
            ref = reference or generate_transaction_reference('WDR')
            if amount > balance.available:
                raise ValueError("Insufficient available balance")
            avail_after = balance.available - amount
            balance.available = avail_after
            balance.save()
            Transaction.objects.create(
                user=user,
                balance=balance,
                transaction_type='withdraw',
                amount=amount,
                sub_balance='available',
                after_balance=avail_after,
                transaction_reference=ref
            )
            PaymentAuditService.audit(user, 'withdraw', amount)
            return ref

    @staticmethod
    def create_deposit_request(user, amount: Decimal):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        reference = generate_transaction_reference('DEP')
        return {
            'amount': amount,
            'reference': reference,
            'payment_message': f"Pay ETB {amount} to [Account/Number], Ref: {reference}",
            'qr_code_data': f"ETB:{amount};REF:{reference}"
        }

    @staticmethod
    def confirm_deposit(user, amount: Decimal, reference: str):
        with db_transaction.atomic():
            if amount <= 0 or not reference:
                raise ValueError("Amount and reference are required for deposit confirmation")
            if Transaction.objects.filter(transaction_reference=reference).exists():
                raise ValueError("Reference already used")
            balance = Balance.objects.select_for_update().get(user=user)
            avail_after = balance.available + amount
            balance.available = avail_after
            balance.save()
            Transaction.objects.create(
                user=user,
                balance=balance,
                transaction_type='deposit',
                amount=amount,
                sub_balance='available',
                after_balance=avail_after,
                transaction_reference=reference
            )
            PaymentAuditService.audit(user, 'deposit_confirmed', amount)
            return True

class EscrowService:
    @staticmethod
    def create_campaign_escrow(advertiser, amount, campaign, reference=None):
        with db_transaction.atomic():
            balance = Balance.objects.select_for_update().get(user=advertiser)
            if balance.available < amount:
                raise ValueError("Insufficient funds")
            ref = reference or generate_transaction_reference('ESC')
            avail_after = balance.available - amount
            escrow_after = balance.escrow + amount
            balance.available = avail_after
            balance.escrow = escrow_after
            balance.save()
            Transaction.objects.create(
                user=advertiser,
                balance=balance,
                transaction_type='debit',
                amount=amount,
                sub_balance='available',
                after_balance=avail_after,
                transaction_reference=f'{ref}-DEB'
            )
            Transaction.objects.create(
                user=advertiser,
                balance=balance,
                transaction_type='credit',
                amount=amount,
                sub_balance='escrow',
                after_balance=escrow_after,
                transaction_reference=f'{ref}-CRE'
            )
            escrow = Escrow.objects.create(
                advertiser=advertiser,
                amount=amount,
                remaining_amount=amount,
                campaign=campaign,
                status=Escrow.EscrowStatus.PENDING
            )
            PaymentAuditService.audit(advertiser, 'create_campaign_escrow', amount, target_type='Escrow', target_id=str(escrow.id))
            return escrow

    @staticmethod
    def cancel(escrow_id):
        with db_transaction.atomic():
            escrow = Escrow.objects.select_for_update().get(id=escrow_id)
            if escrow.status != Escrow.EscrowStatus.PENDING:
                raise ValueError("Only pending escrows can be cancelled.")
            balance = Balance.objects.select_for_update().get(user=escrow.advertiser)
            refund_amount = escrow.remaining_amount
            if refund_amount > 0:
                ref = generate_transaction_reference('ESC')
                escrow_after = balance.escrow - refund_amount
                avail_after = balance.available + refund_amount
                balance.escrow = escrow_after
                balance.available = avail_after
                balance.save()
                Transaction.objects.create(
                    user=escrow.advertiser,
                    balance=balance,
                    transaction_type='debit',
                    amount=refund_amount,
                    sub_balance='escrow',
                    after_balance=escrow_after,
                    transaction_reference=f'{ref}-DEB'
                )
                Transaction.objects.create(
                    user=escrow.advertiser,
                    balance=balance,
                    transaction_type='credit',
                    amount=refund_amount,
                    sub_balance='available',
                    after_balance=avail_after,
                    transaction_reference=f'{ref}-CRE'
                )
            escrow.status = Escrow.EscrowStatus.CANCELLED
            escrow.save()
            PaymentAuditService.audit(escrow.advertiser, 'escrow_cancelled', refund_amount, target_type='Escrow', target_id=str(escrow.id))
            return refund_amount

class EarningService:
    @staticmethod
    def record_earning(escrow_id, creator, amount, reference=None):
        with db_transaction.atomic():
            creator_share = get_creator_share(amount)
            escrow = Escrow.objects.select_for_update().get(id=escrow_id)
            if not escrow.assigned_creators.filter(id=creator.id).exists():
                raise ValueError("Creator not assigned to this escrow.")
            if escrow.status != Escrow.EscrowStatus.PENDING:
                raise ValueError("Escrow is not active.")
            if escrow.remaining_amount < amount:
                raise ValueError("Not enough funds in escrow.")
            advertiser_balance = Balance.objects.select_for_update().get(user=escrow.advertiser)
            creator_balance, _ = Balance.objects.get_or_create(user=creator, type=BalanceType.CREATOR)
            creator_balance = Balance.objects.select_for_update().get(id=creator_balance.id)
            ref = reference or generate_transaction_reference('ERN')
            adv_escrow_after = advertiser_balance.escrow - amount
            advertiser_balance.escrow = adv_escrow_after
            advertiser_balance.save()
            Transaction.objects.create(
                user=escrow.advertiser,
                balance=advertiser_balance,
                transaction_type='spend',
                amount=amount,
                sub_balance='escrow',
                after_balance=adv_escrow_after,
                transaction_reference=f'{ref}-ADV'
            )
            cre_escrow_after = creator_balance.escrow + creator_share
            creator_balance.escrow = cre_escrow_after
            creator_balance.save()
            Transaction.objects.create(
                user=creator,
                balance=creator_balance,
                transaction_type='earning',
                amount=creator_share,
                sub_balance='escrow',
                after_balance=cre_escrow_after,
                transaction_reference=f'{ref}-CRE'
            )
            escrow.remaining_amount -= amount
            if escrow.remaining_amount <= 0:
                escrow.remaining_amount = Decimal('0.00')
                escrow.status = Escrow.EscrowStatus.RELEASED
            escrow.save()
            PaymentAuditService.audit(creator, 'earning_recorded', creator_share, target_type='Escrow', target_id=str(escrow.id))
            PaymentAuditService.audit(escrow.advertiser, 'escrow_funded_creator', amount, target_type='Escrow', target_id=str(escrow.id))
            return ref

    @staticmethod
    def release_earnings(creator):
        with db_transaction.atomic():
            balance = Balance.objects.select_for_update().get(user=creator)
            amount = balance.escrow
            if amount <= 0:
                raise ValueError("No escrow funds to release.")
            ref = generate_transaction_reference('REL')
            escrow_after = balance.escrow - amount
            avail_after = balance.available + amount
            balance.escrow = escrow_after
            balance.available = avail_after
            balance.save()
            Transaction.objects.create(
                user=creator,
                balance=balance,
                transaction_type='debit',
                amount=amount,
                sub_balance='escrow',
                after_balance=escrow_after,
                transaction_reference=f'{ref}-DEB'
            )
            Transaction.objects.create(
                user=creator,
                balance=balance,
                transaction_type='credit',
                amount=amount,
                sub_balance='available',
                after_balance=avail_after,
                transaction_reference=f'{ref}-CRE'
            )
            PaymentAuditService.audit(creator, 'funds_released', amount)
            return amount