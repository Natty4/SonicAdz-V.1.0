from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from api.serializers.creators import UserProfileSerializer, UserUpdateSerializer

User = get_user_model()

class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update user profile.
    """
    serializer_class = UserUpdateSerializer  # Accepts update fields
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserProfileSerializer  # For viewing
        return UserUpdateSerializer       # For editing

    def get_object(self):
        return self.request.user
