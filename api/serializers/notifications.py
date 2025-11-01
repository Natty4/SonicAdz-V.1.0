from rest_framework import serializers
from core.models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    # Add a new CharField to hold the display value
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = Notification
        # Include the new field in the API response
        fields = ['id', 'title', 'message', 'type', 'type_display', 'created_at', 'is_read']
        read_only_fields = ['id', 'created_at']