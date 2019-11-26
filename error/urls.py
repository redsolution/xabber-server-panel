from django.conf.urls import url
from django.views.generic import TemplateView


urlpatterns = [
    url(r'^403/$', TemplateView.as_view(template_name='error/403.html'), name='403'),
]
