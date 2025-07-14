# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserActivity, VendorProfile, CustomerProfile
from django_otp.plugins.otp_static.models import StaticDevice

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    is_2fa_enabled = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'username',
            'role', 'role_display', 'date_joined', 'last_login',
            'is_active', 'is_staff', 'is_2fa_enabled', 'email_verified'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }
    
    def get_is_2fa_enabled(self, obj):
        return obj.requires_2fa

class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'username', 'password', 'role']
        extra_kwargs = {'password': {'write_only': True}}
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password'],
            role=validated_data.get('role', 'customer')
        )
        return user

class ActivitySerializer(serializers.ModelSerializer):
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'user', 'user_email', 'activity_type', 'activity_type_display',
            'ip_address', 'user_agent', 'timestamp'
        ]
        read_only_fields = fields

class VendorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    company_name = serializers.CharField(required=True)
    
    class Meta:
        model = VendorProfile
        fields = [
            'id', 'user', 'company_name', 'business_license_number',
            'website', 'address', 'is_verified', 'created_at', 'updated_at'
        ]

class CustomerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = CustomerProfile
        fields = [
            'id', 'user', 'date_of_birth', 'preferred_contact_method',
            'shipping_address', 'billing_address', 'created_at', 'updated_at'
        ]

class TwoFactorBackupTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticDevice
        fields = ['name', 'created_at']
        read_only_fields = fields

class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

class ToggleTwoFactorSerializer(serializers.Serializer):
    enable = serializers.BooleanField(required=True)

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class SetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, min_length=10)
    confirm_password = serializers.CharField(required=True, min_length=10)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data