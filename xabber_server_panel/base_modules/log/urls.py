from django.urls import path
from .views import ServerLog, DjangoLog


urlpatterns = [
    # server log
    path('', ServerLog.as_view(), name='server_log'),
    path('django_log/', DjangoLog.as_view(), name='django_log'),
]
