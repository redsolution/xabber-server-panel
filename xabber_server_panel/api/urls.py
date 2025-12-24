from django.urls import path, include
from .views import ServicesHash


urlpatterns = [
    path('services_hash/', ServicesHash.as_view(), name='services_hash'),
]
