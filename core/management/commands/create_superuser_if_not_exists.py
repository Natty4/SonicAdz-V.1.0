import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
# Get the logger
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Creates a superuser if it does not already exist'

    def handle(self, *args, **options):
        username = 'admin' 
        phone_number = '+251999666333' 
        email = 'admin@sonicadz.com'
        user_type = 'staff'  
        password = settings.SUPERUSER_PASSWORD

        User = get_user_model()

        # Check if the superuser already exists
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, phone_number=phone_number, user_type=user_type, email=email, password=password)
            logger.info(f'Superuser {username}- -OOO{password}OOO created successfully')
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} created successfully'))
        else:
            logger.info(f'Superuser {username} already exists')
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} already exists'))
