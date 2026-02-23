from rest_framework import serializers
from .models import Profile
from django.contrib.auth.models import User

from .utils import SendMail

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email']

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['fullname', 'gender', 'phone', 'profile_pix']

class RegistrationSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    username = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    
    class Meta:
        model = Profile
        fields = ['fullname', 'username', 'email', 'password1', 'password2', 'gender', 'phone', 'profile_pix']
        extra_kwargs = {
            'gender': {'required': False, 'allow_blank': True, 'allow_null': True},
            'phone': {'required': False, 'allow_blank': True, 'allow_null': True},
            'profile_pix': {'required': False, 'allow_null': True}
        }

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError('Passwords do not match')
        if not data.get('fullname'):
            raise serializers.ValidationError('Fullname must be filled')
        return data
    
    def create(self, validated_data):
        username = validated_data.pop('username')
        email = validated_data.pop('email')
        password = validated_data.pop('password1')
        
        # Handle optional fields with defaults
        gender = validated_data.get('gender', '')
        phone = validated_data.get('phone', '')
        profile_pix = validated_data.get('profile_pix')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        profile = Profile.objects.create(
            user=user,
            fullname=validated_data['fullname'],
            phone=phone,
            gender=gender,
            profile_pix=profile_pix
        )
        
        # Send email (handle silently if fails)
        try:
            SendMail(email)
        except:
            pass  # Email sending failed, but registration succeeds
            
        return profile

class UpdateProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', required=False)
    email = serializers.EmailField(source='user.email', required=False)
    
    class Meta:
        model = Profile
        fields = ['fullname', 'username', 'email', 'gender', 'phone', 'profile_pix']
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        
        if 'username' in user_data:
            user.username = user_data['username']
        if 'email' in user_data:
            user.email = user_data['email']
        user.save()
 
        instance.fullname = validated_data.get('fullname', instance.fullname)
        instance.gender = validated_data.get('gender', instance.gender)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.profile_pix = validated_data.get('profile_pix', instance.profile_pix)
        instance.save()
    
        return instance