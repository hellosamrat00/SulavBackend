from django.urls import path
from .views import ChatAPIView, SignupView, LoginView

urlpatterns = [
    path('ask/', ChatAPIView.as_view(), name='chat-api'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
]
