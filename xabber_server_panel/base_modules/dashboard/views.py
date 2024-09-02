from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import logout
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import reverse

from xabber_server_panel.utils import is_ejabberd_started, start_ejabberd, restart_ejabberd, stop_ejabberd
from xabber_server_panel.base_modules.users.decorators import permission_read, permission_admin
from xabber_server_panel.base_modules.config.utils import check_hosts
from xabber_server_panel.api.utils import get_api
from xabber_server_panel.custom_auth.exceptions import UnauthorizedException


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    @permission_read
    def get(self, request, *args, **kwargs):
        self.api = get_api(request)

        check_hosts(self.api)

        context = {
            'data': self.get_users_data(),
            'started': is_ejabberd_started()
        }
        return self.render_to_response(context)

    @permission_admin
    def post(self, request, *args, **kwargs):

        self.api = get_api(request)

        start = request.POST.get('start')
        restart = request.POST.get('restart')
        stop = request.POST.get('stop')

        if start:
            try:
                self.start_server()
            except UnauthorizedException:
                # stop server and logout if user has no permissions
                stop_ejabberd()
                logout(self.request)
                return HttpResponseRedirect(reverse('custom_auth:login'))
        elif restart:
            restart_ejabberd()
        elif stop:
            stop_ejabberd()

        check_hosts(self.api)
        context = {
            'data': self.get_users_data(),
            'started': is_ejabberd_started()
        }
        return self.render_to_response(context)

    def get_users_data(self):
        hosts = self.request.hosts

        data = {
            'hosts': [
                {
                    'host': host,
                    'total': self.api.get_users_count({"host": host.name}).get('count'),
                    'online': self.api.stats_host({"host": host.name}).get('count')
                }
                 for host in hosts
            ],
        }

        total_count = 0
        online_count = 0

        for entry in data['hosts']:
            total_count += entry.get('total', 0) or 0
            online_count += entry.get('online', 0) or 0

        data['total'] = total_count
        data['online'] = online_count

        return data

    def start_server(self):
        """
            Start server logic:
                * check password
                * set token after server start
        """

        password = self.request.POST.get('password')

        if self.request.user.check_password(password):
            start_ejabberd()

            data = {
                'username': self.request.user.full_jid,
                'password': password
            }

            self.api.login(data)
        else:
            messages.error(self.request, 'Wrong password')