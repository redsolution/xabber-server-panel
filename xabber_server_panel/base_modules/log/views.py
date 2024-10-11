from django.contrib.auth.mixins import LoginRequiredMixin
from xabber_server_panel.mixins import ServerStartedMixin
from django.views.generic import TemplateView
from django.conf import settings
from django.http import HttpResponse, Http404

from xabber_server_panel.base_modules.users.decorators import permission_admin, permission_read

import os


class ServerLog(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    template_name = 'log/server_log.html'

    @permission_read
    def get(self, request, *args, **kwargs):
        try:
            self.lines = int(request.GET.get('lines', 500))
        except:
            self.lines = 500

        self.log_files = [filename for filename in os.listdir(settings.XMPP_SERVER_LOG_DIR) if filename.endswith('.log')]

        file = request.GET.get('file')
        if file and file in self.log_files:
            self.log_path = os.path.join(settings.XMPP_SERVER_LOG_DIR, file)
        else:
            self.log_path = settings.XMPP_SERVER_LOG_FILE

        log = self.get_log()
        full = request.GET.get('full')
        if full:
            return self.full_logfile()

        context = {
            'log': log,
            'log_files': self.log_files,
            'log_path': self.log_path
        }
        if request.is_ajax():
            self.template_name = 'log/parts/log_list.html'

        return self.render_to_response(context)

    def get_log(self):
        if os.path.exists(self.log_path):
            with open(self.log_path, 'r') as f:
                log = f.readlines()
                return log[-self.lines:]

    def full_logfile(self):
        # Open the file in read mode
        if os.path.exists(self.log_path):
            with open(self.log_path, 'rb') as log_file:
                # Create a response object
                response = HttpResponse(log_file.read(), content_type='text/plain')
                response['Content-Disposition'] = f'inline; filename={os.path.basename(self.log_path)}'
                return response
        else:
            raise Http404


class DjangoLog(ServerStartedMixin, LoginRequiredMixin, TemplateView):

    template_name = 'log/django_log.html'

    @permission_read
    def get(self, request, *args, **kwargs):
        try:
            self.lines = int(request.GET.get('lines', 500))
        except:
            self.lines = 500

        self.log_files = [filename for filename in os.listdir(settings.DJANGO_LOG_DIR) if filename.endswith('.log')]

        file = request.GET.get('file')
        if file and file in self.log_files:
            self.log_path = os.path.join(settings.DJANGO_LOG_DIR, file)
        else:
            self.log_path = settings.DJANGO_LOG

        log = self.get_log()
        full = request.GET.get('full')
        if full:
            return self.full_logfile()

        context = {
            'log': log,
            'log_files': self.log_files,
            'log_path': self.log_path
        }

        if request.is_ajax():
            self.template_name = 'log/parts/log_list.html'

        return self.render_to_response(context)

    def get_log(self):
        if os.path.exists(self.log_path):
            with open(self.log_path, 'r') as f:
                log = f.readlines()
                return log[-self.lines:]

    def full_logfile(self):
        # Open the file in read mode
        if os.path.exists(self.log_path):
            with open(self.log_path, 'rb') as log_file:
                # Create a response object
                response = HttpResponse(log_file.read(), content_type='text/plain')
                response['Content-Disposition'] = f'inline; filename={os.path.basename(self.log_path)}'
                return response
        else:
            raise Http404