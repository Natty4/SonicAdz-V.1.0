# Manually Generated on 2025-10-11 21:26

from django.db import migrations, models

def migrate_balance_after_transaction(apps, schema_editor):
    Transaction = apps.get_model('payments', 'Transaction')
    # Copy data from balance_after_transaction to after_balance
    for transaction in Transaction.objects.all():
        transaction.after_balance = transaction.balance_after_transaction
        transaction.save()

class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0004_rename_locked_balance_escrow_and_more'),
    ]

    operations = [
        # Ensure after_balance is nullable temporarily to avoid NOT NULL errors
        migrations.AlterField(
            model_name='Transaction',
            name='after_balance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True),
        ),
        # Copy data from balance_after_transaction to after_balance
        migrations.RunPython(
            code=migrate_balance_after_transaction,
            reverse_code=migrations.RunPython.noop,
        ),
        # Remove the old balance_after_transaction field
        migrations.RemoveField(
            model_name='Transaction',
            name='balance_after_transaction',
        ),
        # Make after_balance non-nullable again
        migrations.AlterField(
            model_name='Transaction',
            name='after_balance',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
    ]