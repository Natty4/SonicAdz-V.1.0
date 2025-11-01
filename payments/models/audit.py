from django.db import models

from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditLog(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE)
    
    action_type = models.CharField(
        max_length=100)
    
    target_type = models.CharField(
        max_length=100)
    
    target_id = models.CharField(
        max_length=255)
    description = models.TextField()
    timestamp = models.DateTimeField(
        auto_now_add=True)
    
    def __str__(self):
        return f"Action: {self.action_type} on \
            {self.target_type} ID \
                {self.target_id} by \
                    {self.user.username}"