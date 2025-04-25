from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import ChatRequestSerializer
from .gemini_bot import get_bot_response
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserSerializer, LoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework import status
from .serializers import UserSerializer, LoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from rest_framework import status
from .serializers import UserSerializer, LoginSerializer
from .models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny




ACCESS_TOKEN = "EAATQ57NiJdoBO3D3Apk6N9CkEM7FQGtU2Ny58WdgQC4WJsIKzmQEOpdoOavW56GGFuJBZA3EVsEtaBpdCXxPaLnJ21BqASoQbvXYuimVNtjjVyy6MXt2iXTHXWVoQzNvTQJklFz4N4COMFOiAWosjZC3JkOgPLyIW5zV9HFljNVI4wZCNhtmRSvhDIJXeCFd3RIUvv35FKRcXvJ2gU0Pqk1jvsZD_ACCESS_TOKEN"
PHONE_NUMBER_ID = "642846638913647"
WHATSAPP_API_URL = f"https://graph.facebook.com/v19.0/{642846638913647}/messages"

class ChatAPIView(APIView):
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if serializer.is_valid():
            question = serializer.validated_data['question']
            response = get_bot_response(question)
            return Response({"response": response})
        return Response(serializer.errors, status=400)



class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    refresh = RefreshToken.for_user(user)
                    return Response({
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'user': UserSerializer(user).data
                    })
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
            except User.DoesNotExist:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
