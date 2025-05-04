from rest_framework import serializers
from .models import User, Booking, HairService


class ChatRequestSerializer(serializers.Serializer):
    question = serializers.CharField()
    

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'role', 'password','date_joined']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            phone=validated_data.get('phone', ''),
            role=validated_data.get('role', 'user')
        )
        user.set_password(validated_data['password'])
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    
class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    service = serializers.CharField(source='service.name', read_only=True, allow_null=True)

    class Meta:
        model = Booking
        fields = ['id', 'user', 'service', 'appointment_time', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'service', 'appointment_time', 'created_at', 'updated_at']
        
class HairServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HairService
        fields = ['id', 'name', 'price']