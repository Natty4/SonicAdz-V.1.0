import hashlib
import json
import os
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import ProgrammingError
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.db.models.fields.related import ManyToManyField

IGNORED_FIELDS = {'created_at', 'updated_at', 'last_login', 'date_joined', 'password'}

def get_record_hash(instance, ignore_fields=None):
    """
    Create a hash of a model instance's data, excluding ignored fields,
    and converting related model instances to their PKs.
    """
    if ignore_fields is None:
        ignore_fields = IGNORED_FIELDS

    data = {}
    for field in instance._meta.fields:
        name = field.name
        if name in ignore_fields:
            continue
        try:
            value = getattr(instance, name)
            # If it's a related model instance, store its PK instead
            if hasattr(field, 'remote_field') and field.remote_field:
                value = value.pk if value else None
        except Exception:
            value = None
        data[name] = value

    string = json.dumps(data, sort_keys=True)
    return hashlib.md5(string.encode()).hexdigest()


def get_m2m_data(instance):
    """Return a dict of M2M field name -> set of related primary keys."""
    m2m_data = {}
    for field in instance._meta.many_to_many:
        try:
            m2m_qs = getattr(instance, field.name).all()
            m2m_data[field.name] = set(m2m_qs.values_list('pk', flat=True))
        except Exception:
            m2m_data[field.name] = set()
    return m2m_data


class Command(BaseCommand):
    help = "Backs up all model data from the default DB to the Supabase DB."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Simulate changes without saving')
        parser.add_argument('--quiet', action='store_true', help='Suppress standard output (errors still shown)')
        parser.add_argument('--log', type=str, help='Write backup logs to this file path')

    def log(self, message, options, error=False):
        if not options['quiet'] or error:
            (self.stderr if error else self.stdout).write(message)
        if options.get('log'):
            with open(options['log'], 'a') as log_file:
                log_file.write(f"[{timezone.now()}] {message}\n")

    def handle(self, *args, **options):
        supabase_db = 'supabase'
        default_db = 'default'
        dry_run = options['dry_run']

        self.log("🚀 Starting backup to Supabase...", options)

        all_models = apps.get_models()
        global_inserted = global_updated = global_skipped = global_errors = global_m2m_synced = 0

        for model in all_models:
            model_name = model._meta.label

            if not model._meta.managed or model._meta.abstract:
                self.log(f"⚠️  Skipping unmanaged/abstract model: {model_name}", options)
                continue

            try:
                default_records = model.objects.using(default_db).all()
                count = default_records.count()
                inserted = updated = skipped = errors = m2m_synced = 0

                self.log(f"📦 Backing up {model_name} ({count} records)...", options)

                for record in default_records:
                    try:
                        supabase_record = model.objects.using(supabase_db).get(pk=record.pk)

                        record_hash = get_record_hash(record)
                        supabase_hash = get_record_hash(supabase_record)

                        if record_hash != supabase_hash:
                            if not dry_run:
                                with transaction.atomic(using=supabase_db):
                                    record.save(using=supabase_db)
                            updated += 1
                        else:
                            skipped += 1

                        # 🔁 Handle Many-to-Many fields
                        default_m2m = get_m2m_data(record)
                        supabase_m2m = get_m2m_data(supabase_record)

                        for field_name in default_m2m:
                            if default_m2m[field_name] != supabase_m2m[field_name]:
                                if not dry_run:
                                    getattr(supabase_record, field_name).set(default_m2m[field_name], using=supabase_db)
                                m2m_synced += 1

                    except model.DoesNotExist:
                        if not dry_run:
                            with transaction.atomic(using=supabase_db):
                                record.save(using=supabase_db)
                                # Save M2M after instance saved
                                m2m_data = get_m2m_data(record)
                                for field_name, related_pks in m2m_data.items():
                                    getattr(record, field_name).set(related_pks, using=supabase_db)
                        inserted += 1

                    except Exception as e:
                        errors += 1
                        self.log(f"* Error processing {model_name} pk={record.pk}: {e}", options, error=True)

                self.log(
                    f"✅ {model_name}: {inserted} inserted, {updated} updated, {skipped} unchanged, "
                    f"{m2m_synced} M2M synced, {errors} errors", options
                )

                global_inserted += inserted
                global_updated += updated
                global_skipped += skipped
                global_errors += errors
                global_m2m_synced += m2m_synced

            except ProgrammingError as e:
                self.log(f"⚠️ Skipping {model_name} (DB not ready?): {e}", options, error=True)
            except Exception as e:
                self.log(f"* Failed to process {model_name}: {e}", options, error=True)

        self.log("🎉 Backup complete!", options)
        self.log(
            f"📊 Summary: {global_inserted} inserted, {global_updated} updated, "
            f"{global_skipped} skipped, {global_m2m_synced} M2M synced, {global_errors} errors", options
        )
