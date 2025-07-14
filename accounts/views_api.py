from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django_otp.plugins.otp_static.models import StaticDevice

from .models import UserActivity, VendorProfile, CustomerProfile
from .serializers import (
    UserSerializer, ActivitySerializer, VendorProfileSerializer,
    CustomerProfileSerializer, ToggleTwoFactorSerializer,
    VerifyEmailSerializer, PasswordResetSerializer, SetPasswordSerializer,
    UserCreateSerializer, TwoFactorBackupTokenSerializer
)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'list']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='my-profile')
    def my_profile(self, request):
        user = request.user
        if user.is_vendor():
            profile = VendorProfile.objects.get(user=user)
            serializer = VendorProfileSerializer(profile)
        else:
            profile = CustomerProfile.objects.get(user=user)
            serializer = CustomerProfileSerializer(profile)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='send-activation')
    def send_activation(self, request, pk=None):
        user = self.get_object()
        # Implementation would go here
        return Response({'status': 'Activation email sent'})

class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserActivity.objects.filter(user=self.request.user).order_by('-timestamp')

class VendorProfileViewSet(viewsets.ModelViewSet):
    queryset = VendorProfile.objects.all()
    serializer_class = VendorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return VendorProfile.objects.all()
        return VendorProfile.objects.filter(user=self.request.user)

class CustomerProfileViewSet(viewsets.ModelViewSet):
    queryset = CustomerProfile.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return CustomerProfile.objects.all()
        return CustomerProfile.objects.filter(user=self.request.user)

class ToggleTwoFactorAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ToggleTwoFactorSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            user.requires_2fa = serializer.validated_data['enable']
            user.save()
            return Response({
                'status': 'success',
                'requires_2fa': user.requires_2fa
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyEmailAPI(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if serializer.is_valid():
            try:
                uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
                user = User.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                user = None
                
            if user and default_token_generator.check_token(user, serializer.validated_data['token']):
                user.email_verified = True
                user.is_active = True
                user.save()
                return Response({'status': 'Email verified'})
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetAPI(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            # Implementation would send reset email
            return Response({'status': 'Password reset email sent'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SetPasswordAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'status': 'Password updated'})
        
        if getattr(request, 'limited', False):
            return Response({'error': 'Too many requests'}, status=429)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TwoFactorBackupTokensAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        tokens = StaticDevice.objects.filter(user=request.user, name='backup')
        serializer = TwoFactorBackupTokenSerializer(tokens, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        device, created = StaticDevice.objects.get_or_create(
            user=request.user, 
            name='backup'
        )
        device.token_set.all().delete()
        tokens = device.generate_tokens(10)
        return Response({
            'status': 'Backup tokens regenerated',
            'tokens': tokens
        })