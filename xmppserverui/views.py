import mimetypes

from django.http import HttpResponsePermanentRedirect, FileResponse, HttpResponseRedirect, Http404
from django.views.generic import View, TemplateView, RedirectView
from django.urls import reverse
from django.contrib.auth import login

from django.conf import settings
from .utils import get_default_url, get_xabber_web_suffix
from xmppserverui.mixins import ServerInstalledMixin
from virtualhost.models import User
from server.utils import *
from api.models import EjabberdAccount


class DefaultView(View):
    def get(self, request):
        username = request.session.get('_auth_user_username')
        host = request.session.get('_auth_user_host')
        if username and host:
            user = User.objects.filter(username=username, host=host)
            if user.exists():
                user = user[0]
                return HttpResponseRedirect(get_default_url(request.user, django_user=user))
        return HttpResponseRedirect(get_default_url(request.user))


class XabberWebView(ServerInstalledMixin, TemplateView):
    template_name = 'xabberweb/index.html'

    def get(self, request, *args, **kwargs):
        try:
            settings.XABBER_WEB_VERSION
        except:
            settings.XABBER_WEB_VERSION = get_xabber_web_suffix()

        username = request.session.get('_auth_user_username')
        host = request.session.get('_auth_user_host')
        account_token = ""
        token_fetched = False
        if isinstance(request.user, EjabberdAccount):
            token_fetched = True
            account_token = request.user.api.token
            # account_token = request.user.api.request_token(username=username, ip="", browser="")['token']
        account_jid = ""
        if username and host:
            account_jid = "%s@%s" % (username, host) if username and host else None
        else:
            token_fetched = False
        context = {
            'token_fetched': token_fetched,
            'account_jid': account_jid,
            'account_token': account_token,
            'xabber_web_ver': settings.XABBER_WEB_VERSION
        }
        return self.render_to_response(context)


class XabberWebStaticView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponsePermanentRedirect(settings.STATIC_URL + 'xabberweb' + request.path)


class XabberWebFirebaseMessSWView(View):
    def get(self, request, *args, **kwargs):
        path = settings.STATIC_ROOT + '/xabberweb/firebase-messaging-sw.js'
        content_type, encoding = mimetypes.guess_type(str(path))
        content_type = content_type or 'application/octet-stream'
        try:
            response = FileResponse(open(path),
                                    content_type=content_type)
        except:
            raise Http404

        return response
