from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from virtualhost.models import VirtualHost, User
from server.models import LDAPSettings
from server.utils import is_ejabberd_running
from .utils import get_default_url, is_xmpp_server_installed


class BaseMixin(object):
    permission_methods = []
    extra_init_methods = []

    def get_init_methods(self):
        return self.permission_methods + self.extra_init_methods

    def dispatch(self, request, *args, **kwargs):
        for method_name in self.get_init_methods():
            method = getattr(self, method_name)
            response = method(request, *args, **kwargs)
            if response:
                return response
        return super(BaseMixin, self).dispatch(request, *args, **kwargs)


class ServerInstalledMixin(BaseMixin):
    permission_methods = ['is_server_installed']

    def is_server_installed(self, request, *args, **kwargs):
        if not is_xmpp_server_installed():
            return HttpResponseRedirect(get_default_url(request.user))


class NoAuthMixin(ServerInstalledMixin):
    permission_methods = ServerInstalledMixin.permission_methods + ['is_anonymous']

    def is_anonymous(self, request, *args, **kwargs):
        if not request.user.is_anonymous():
            return HttpResponseRedirect(get_default_url(request.user))


class AuthMixin(ServerInstalledMixin):
    permission_methods = ServerInstalledMixin.permission_methods + ['is_authenticated']

    def is_authenticated(self, request, *args, **kwargs):
        if request.user.is_anonymous():
            return HttpResponseRedirect(get_default_url(request.user))


class AdminMixin(AuthMixin):
    permission_methods = ['is_admin']

    def is_admin(self, request, *args, **kwargs):
        if request.user.is_anonymous():
            return HttpResponseRedirect(get_default_url(request.user))
        username = request.session.get('_auth_user_username')
        host = request.session.get('_auth_user_host')
        user = User.objects.filter(username=username, host=host)
        if user.exists():
            user = user[0]
            if not user.is_admin:
                return HttpResponseRedirect(reverse('personal-area:profile'))


class PageContextMixin(AdminMixin):
    permission_methods = AdminMixin.permission_methods + ['is_valid_token']
    extra_init_methods = ['init_page_context', 'fill_page_context']

    def is_valid_token(self, request, *args, **kwargs):
        request.user.api.registered_vhosts(data={})
        if request.user.api.status_code == 401:
            return HttpResponseRedirect(reverse('auth:logout'))

    def init_page_context(self, request, *args, **kwargs):
        username = request.session.get('_auth_user_username')
        host = request.session.get('_auth_user_host')
        try:
            user = User.objects.get(username=username, host=host)
        except User.DoesNotExist:
            user = None

        page_data = {'section': getattr(self, 'page_section', '')}
        page_data.update(kwargs)

        need_to_request_user_pass = request.user.api.token is None \
                                    and is_ejabberd_running()['success']

        vhosts = VirtualHost.objects.all().order_by('id')
        vhost_ids = [o.ldap_vhost.id for o in
                     LDAPSettings.objects.filter(is_enabled=True)]
        vhosts_cr = vhosts.exclude(id__in=vhost_ids)

        self.context = {'page': page_data,
                        'auth_user': user,
                        'need_to_request_user_pass': need_to_request_user_pass,
                        'vhosts': vhosts,
                        'vhosts_cr': vhosts_cr}

    def fill_page_context(self, request, *args, **kwargs):
        pass

    def get_context_data(self, **kwargs):
        return self.context

    def render_to_response(self, context, **response_kwargs):
        self.context.update(context)
        return super(PageContextMixin, self).render_to_response(self.context, **response_kwargs)


class ServerStartedMixin(PageContextMixin):
    permission_methods = PageContextMixin.permission_methods + ['is_server_started']

    def is_server_started(self, request, *args, **kwargs):
        if not is_ejabberd_running()['success']:
            return HttpResponseRedirect(reverse('server:stopped-stub'))
