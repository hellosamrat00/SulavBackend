from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import ChatRequestSerializer, UserSerializer, LoginSerializer, BookingSerializer, HairServiceSerializer
from .gemini_bot import get_bot_response
from .models import User, Booking,HairService
import logging
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth


logger = logging.getLogger(__name__)

class UserListView(APIView):
    def get(self, request):
        users = User.objects.filter(role='user').order_by('username')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

class ChatAPIView(APIView):
    def post(self, request):
        logger.info(f"ChatAPIView: User: {request.user}")
        serializer = ChatRequestSerializer(data=request.data)
        if serializer.is_valid():
            question = serializer.validated_data['question']
            response = get_bot_response(question, request)
            return Response({"response": response})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    refresh = RefreshToken.for_user(user)
                    logger.info(f"Login successful for {email}")
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
    def post(self, request):
        logger.info(f"Signup data: {request.data}")
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            logger.info(f"Signup successful for {user.email}")
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        logger.error(f"Signup failed: {serializer.errors}")
        return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    
class BookingListView(APIView):
    def get(self, request):
        bookings = Booking.objects.select_related('user', 'service').all().order_by('-appointment_time')
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

class BookingUpdateView(APIView):
    def patch(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = BookingSerializer(booking, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class HairServiceListCreateView(APIView):
    def get(self, request):
        services = HairService.objects.all().order_by('name')
        serializer = HairServiceSerializer(services, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = HairServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class HairServiceDetailView(APIView):
    def get(self, request, pk):
        try:
            service = HairService.objects.get(pk=pk)
        except HairService.DoesNotExist:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = HairServiceSerializer(service)
        return Response(serializer.data)

    def put(self, request, pk):
        try:
            service = HairService.objects.get(pk=pk)
        except HairService.DoesNotExist:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = HairServiceSerializer(service, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            service = HairService.objects.get(pk=pk)
        except HairService.DoesNotExist:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class SalesOverviewView(APIView):
    def get(self, request):
        sales = (
            Booking.objects.filter(status='COMPLETED', appointment_time__year=2025)
            .annotate(month=TruncMonth('appointment_time'))
            .values('month')
            .annotate(total=Sum('service__price'))
            .order_by('month')
        )
        data = [
            {
                'name': sale['month'].strftime('%b'),
                'total': float(sale['total']) if sale['total'] else 0
            }
            for sale in sales
        ]
        return Response(data)