# campaigns/permissions.py
from rest_framework import permissions
from users.models import UserType
import logging

logger = logging.getLogger(__name__)

# Permissions
class IsAdvertiser(permissions.BasePermission):
    """
    Custom permission to only allow authenticated users with user_type='advertiser' 
    to access the view.
    """
    message = 'Access denied. Only authenticated advertisers are permitted.'

    def has_permission(self, request, view):
        # 1. Check Authentication
        if not request.user.is_authenticated:
            logger.error(f"Permission denied: User not authenticated.")
            return False
        
        # 2. Check User Type
        # Ensure the User model has the 'user_type' attribute
        if not hasattr(request.user, 'user_type'):
            logger.error(f"User model is missing 'user_type' attribute.")
            # Deny access if user type cannot be determined securely
            return False 
        
        if request.user.user_type != UserType.ADVERTISER:
            logger.warning(f"Permission denied: User {request.user} is not an 'advertiser' (Type: {request.user.user_type}).")
            return False
            
        return True

    

class IsOwnerOfCampaignOrAd(permissions.BasePermission):
    """
    Custom permission to only allow the campaign's advertiser (owner) 
    to view or edit the object (Campaign or Ad).
    """
    message = 'Access denied. You do not own this campaign or ad content.'
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any advertiser (already checked by IsAdvertiser)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions (POST, PUT, PATCH, DELETE) only allowed to the owner.
        
        # Check for Ad object (has a 'campaign' field)
        if hasattr(obj, 'campaign'): 
            is_owner = obj.campaign.advertiser == request.user
            logger.debug(f"Ad {obj.id} ownership check: {is_owner} for user {request.user}")
            return is_owner
        
        # Check for Campaign object (has an 'advertiser' field)
        elif hasattr(obj, 'advertiser'):
            is_owner = obj.advertiser == request.user
            logger.debug(f"Campaign {obj.id} ownership check: {is_owner} for user {request.user}")
            return is_owner
            
        # Fallback for unexpected objects (shouldn't happen in our ViewSets)
        logger.warning(f"Unexpected object type {type(obj)} in IsOwner permission.")
        return False

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users to perform actions.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff