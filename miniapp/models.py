from django.db import models

class TelegramVisitorLog(models.Model):
    telegram_id = models.BigIntegerField(null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    is_premium = models.BooleanField(default=False)
    
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()

    device_type = models.CharField(max_length=50, null=True, blank=True)  # mobile / tablet / pc
    os = models.CharField(max_length=50, null=True, blank=True)
    browser = models.CharField(max_length=50, null=True, blank=True)
    device_name = models.CharField(max_length=100, null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)