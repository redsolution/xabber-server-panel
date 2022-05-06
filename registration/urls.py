from django.conf.urls import url
from .views import RegistrationView, ChangeKeyView, AddKeyView, SetUrlView
from xmppserverui.decorators import custom_permission_required

app_name = 'xmppserverui'

urlpatterns = [
    url(r'^$', custom_permission_required('is_admin')(RegistrationView.as_view()), name='registration'),
    url(r'keys/change/(?P<key>[-\w]+)/$', custom_permission_required('is_admin')(ChangeKeyView.as_view()),
        name='change-key'),
    url(r'keys/add/$', custom_permission_required('is_admin')(AddKeyView.as_view()), name='add-key'),
    url(r'url/$', custom_permission_required('is_admin')(SetUrlView.as_view()), name='set-url'),
]
