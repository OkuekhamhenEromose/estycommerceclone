from django.shortcuts import redirect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, login, logout
from .serializers import UserSerializer,UpdateProfileSerializer,RegistrationSerializer
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

# registration
class RegistrationView(APIView):
    permission_classes = [AllowAny]
    # def get(self,request):
    #     if request.user.is_authenticated:
    #         return redirect('dashboard')
    def post(self,request):
        try:
            logger.info(f"Registration attempt with data: {request.data}")
            serializer = RegistrationSerializer(data=request.data)
            if serializer.is_valid():
                profile = serializer.save()
                user = profile.user
                return Response({
                    "message": "Registration successful! Please check your email.",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "fullname": profile.fullname,
                        "gender": profile.gender,
                        "phone": profile.phone,
                        "profile_pix": profile.profile_pix.url if profile.profile_pix else None
                    }
                }, status=status.HTTP_201_CREATED)
            logger.error(f"Registration validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Registration error")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Login
class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self,request):
        try:
            username = request.data.get('username', '')
            email = request.data.get('email', '')
            password = request.data.get('password')
            if not username and email:
                try:
                    user_obj = User.objects.get(email=email)
                    username = user_obj.username
                except User.DoesNotExist:
                    pass
            
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request,user)
                from .models import Profile
                profile, created = Profile.objects.get_or_create(user=user)
                return Response({
                    "message": "Login successful!",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "fullname": profile.fullname,
                        "gender": profile.gender,
                        "phone": profile.phone,
                        "profile_pix": profile.profile_pix.url if profile.profile_pix else None
                    }
                }, status=status.HTTP_200_OK)
            return Response({
                "error": "Invalid username/email or password"
            }, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.exception("Login error")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Logout
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self,request):
        try:
            logout(request)
            return Response({"Message":"Logout Successful!"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error':str(e)}, status = status.HTTP_INTERNAL_SERVER_ERROR)

# dashboard
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            profile = request.user.profile
            return Response({
                "message": f"Welcome {profile.fullname}",
                "user": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "email": request.user.email,
                    "fullname": profile.fullname,
                    "gender": profile.gender,
                    "phone": profile.phone,
                    "profile_pix": profile.profile_pix.url if profile.profile_pix else None
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
            serializer = UpdateProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            profile = request.user.profile
            serializer = UpdateProfileSerializer(profile, data=request.data, partial=True)  # allow partial updates
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "message": "Profile updated successfully",
                    "user": {
                        "id": request.user.id,
                        "username": request.user.username,
                        "email": request.user.email,
                        "fullname": profile.fullname,
                        "gender": profile.gender,
                        "phone": profile.phone,
                        "profile_pix": profile.profile_pix.url if profile.profile_pix else None
                    }
                }, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
