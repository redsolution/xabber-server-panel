from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

from django.forms.models import model_to_dict

from xabber_server_panel.base_modules.modules.models import XServicesToken


class ModulesMiddleware(MiddlewareMixin):

    def process_request(self, request):

        if request.user.is_authenticated and request.user.is_admin:
            xs_token = XServicesToken.objects.filter(expires__gt=timezone.now()).first()
            request.session['xs_token'] = model_to_dict(xs_token, exclude=('id', 'expires')) if xs_token else None