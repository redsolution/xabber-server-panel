from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from django.contrib.auth import logout

from xabber_server_panel.custom_auth.exceptions import UnauthorizedException


class UnauthorizedMiddleware(MiddlewareMixin):

    def process_exception(self, request, exception):

        # logout user if user is unauthorized on server
        if isinstance(exception, UnauthorizedException):
            logout(request)
            return HttpResponseRedirect(reverse('custom_auth:login'))

        return None