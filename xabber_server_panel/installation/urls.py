from django.urls import path
from .views import Steps, Success, Quick


urlpatterns = [
    path('steps/', Steps.as_view(), name='steps'),
    path('quick/', Quick.as_view(), name='quick'),
    path('success/', Success.as_view(), name='success'),
]
