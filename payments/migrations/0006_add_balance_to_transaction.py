from django.db import migrations, models
import django.db.models.deletion

def populate_balance_field(apps, schema_editor):
    Transaction = apps.get_model('payments', 'Transaction')
    Balance = apps.get_model('payments', 'Balance')
    for transaction in Transaction.objects.all():
        try:
            balance = Balance.objects.get(user=transaction.user)
            transaction.balance = balance
            transaction.save()
        except Balance.DoesNotExist:
            # Skip transactions for users without a balance
            pass

class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0005_fix_transaction_after_balance'),
    ]

    operations = [
        migrations.AddField(
            model_name='Transaction',
            name='balance',
            field=models.ForeignKey(
                null=True,  # Temporarily nullable for migration
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transactions',
                to='payments.balance'
            ),
        ),
        migrations.RunPython(
            code=populate_balance_field,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='Transaction',
            name='balance',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transactions',
                to='payments.balance'
            ),
        ),
    ]