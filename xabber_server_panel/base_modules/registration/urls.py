from django.urls import path
from .views import RegistrationList, RegistrationCreate, RegistrationUrlView, RegistrationChange, RegistrationDelete


urlpatterns = [
    path('', RegistrationList.as_view(), name='list'),
    path('create/', RegistrationCreate.as_view(), name='create'),
    path('change/<str:key>/', RegistrationChange.as_view(), name='change'),
    path('delete/<str:key>/', RegistrationDelete.as_view(), name='delete'),
    path('url/', RegistrationUrlView.as_view(), name='url'),
]
