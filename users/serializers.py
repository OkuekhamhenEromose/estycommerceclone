from rest_framework import serializers
from . models import Profile
from django.contrib.auth.models import User

from . utils import SendMail
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username','email']

class ProfileSerailizer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['fullname','gender','phone','profile_pix']

class RegistrationSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    username = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    class Meta:
        model =Profile
        fields=['fullname','username','email','password1','password2','gender','phone','profile_pix']

    def validate(self,data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError('Password does not match')
        if not data['fullname']:
            raise serializers.ValidationError('Fullname must be fill')
        return data
    
    def create(self,validated_data):
        username = validated_data.pop('username')
        email = validated_data.pop('email')
        password = validated_data.pop('password1')

        user = User.objects.create_user(username=username,email=email,password=password)

        profile = Profile.objects.create(
            user = user,
            fullname =validated_data['fullname'],
            phone =validated_data['phone'],
            gender =validated_data['gender'],
            profile_pix =validated_data.get('profile_pix')
        )
        SendMail(email)
        return profile


class UpdateProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username',required=False)
    email = serializers.EmailField(source='user.email',required=False)
    class Meta:
        model =Profile
        fields=['fullname','username','email','gender','phone','profile_pix']
    def update(self,instance,validated_data):
        user_data = validated_data.pop('user',{})
        user = instance.user
        if 'username' in user_data:
            user.username = user_data['username']
        if 'email' in user_data:
            user.email = user_data['email']
        user.save()
 
        instance.fullname = validated_data.get('fullname')
        instance.gender = validated_data.get('gender')
        instance.phone = validated_data.get('phone')
        instance.profile_pix = validated_data.get('profile_pix')
        instance.save()
    
        return instance
