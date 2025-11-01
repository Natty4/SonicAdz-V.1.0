from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework import permissions, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from core.models import Notification
from api.serializers.notifications import NotificationSerializer
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.http import Http404

User = get_user_model()


class NotificationListCreateView(GenericAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_read', 'type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user, is_active=True)

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Only admins can create custom notifications.")
        
        user_id = request.data.get('user_id')
        if not user_id:
            raise ValidationError("user_id is required for custom notifications.")
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValidationError("Invalid user_id.")
        
        # Use the get_serializer method to get the serializer instance
        # This ensures the view's serializer_class is used
        serializer = self.get_serializer(data=request.data)
        
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user, type='custom')
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class NotificationDetailView(GenericAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user, is_active=True)

    def get_object(self):
        pk = self.kwargs.get('pk')
        try:
            return self.get_queryset().get(pk=pk)
        except Notification.DoesNotExist:
            raise Http404

    def get(self, request, pk, *args, **kwargs):
        notification = self.get_object()
        serializer = self.get_serializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk, *args, **kwargs):
        notification = self.get_object()
        serializer = self.get_serializer(notification, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk, *args, **kwargs):
        notification = self.get_object()
        notification.is_active = False
        notification.save()
        return Response({'status': 'notification cleared'}, status=status.HTTP_204_NO_CONTENT)

class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk, *args, **kwargs):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user, is_active=True)
        except Notification.DoesNotExist:
            raise Http404
        notification.is_read = True
        notification.save()
        return Response({'status': 'notification marked as read'}, status=status.HTTP_200_OK)

class NotificationMarkUnreadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk, *args, **kwargs):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user, is_active=True)
        except Notification.DoesNotExist:
            raise Http404
        notification.is_read = False
        notification.save()
        return Response({'status': 'notification marked as unread'}, status=status.HTTP_200_OK)

class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        updated = Notification.objects.filter(user=request.user, is_active=True, is_read=False).update(is_read=True)
        return Response(
            {'status': f'{updated} notifications marked as read'},
            status=status.HTTP_200_OK
        )

class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        unread_count = Notification.objects.filter(user=request.user, is_read=False, is_active=True).count()
        return Response({'unread_count': unread_count}, status=status.HTTP_200_OK)