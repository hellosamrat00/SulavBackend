# barbershop/urls.py
from django.urls import path
from .views import   UserListView,ChatAPIView, LoginView, SignupView, BookingListView, BookingUpdateView,HairServiceListCreateView, HairServiceDetailView, SalesOverviewView

urlpatterns = [
    path('api/ask/', ChatAPIView.as_view(), name='ask'),
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/signup/', SignupView.as_view(), name='signup'),
     path('api/users/', UserListView.as_view(), name='user-list'),
    path('api/bookings/', BookingListView.as_view(), name='booking-list'),
    path('api/bookings/<int:pk>/', BookingUpdateView.as_view(), name='booking-update'),
    path('api/services/', HairServiceListCreateView.as_view(), name='service-list-create'),
    path('api/services/<int:pk>/', HairServiceDetailView.as_view(), name='service-detail'),
    path('api/sales-overview/', SalesOverviewView.as_view(), name='sales-overview'),
]