import uuid
from datetime import timedelta
from django.utils import timezone

from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

from django.contrib.auth import get_user_model


User = get_user_model()

class Organization(models.Model):
    name = models.CharField(max_length=255)
    owner = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='owned_organization', 
        limit_choices_to={'user_type':'advertiser'}
        )
    members = models.ManyToManyField(
        User, 
        related_name='organization', 
        limit_choices_to={'user_type':'advertiser'}
        )
    
    
    # Created & Updated timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} (Owner: {self.owner.username})"
    
    def can_add_member(self):
        return self.members.count() < 3
    
    

class Invitation(models.Model):
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name='invitations'
        )
    phone_number = PhoneNumberField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def renew(self):
        if self.accepted:
            self.save()
        self.token = uuid.uuid4()
        self.invited_at = timezone.now()
        self.expires_at = timezone.now() + timedelta(days=7)
        self.accepted = False
        self.save()
    
    def __str__(self):
        return f"Invite to {self.phone_number} for {self.organization.name}"
    