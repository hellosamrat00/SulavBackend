from django.contrib import admin
from .models import User ,Booking, FAQ, HairService


admin.site.register(HairService)
admin.site.register(User)
admin.site.register(Booking)
admin.site.register(FAQ)