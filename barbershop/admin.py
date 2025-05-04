from django.contrib import admin
from .models import HairService  
from .models import User ,Booking


admin.site.register(HairService)
admin.site.register(User)
admin.site.register(Booking)