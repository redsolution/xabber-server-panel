from django.utils.deprecation import MiddlewareMixin

from xabber_server_panel.base_modules.config.models import VirtualHost


class VirtualHostMiddleware(MiddlewareMixin):

    def process_request(self, request):

        if request.user.is_authenticated:
            hosts = VirtualHost.objects.all()

            # set host list
            if not request.user.is_admin:
                hosts = hosts.filter(name=request.user.host)

            request.hosts = hosts

            # set current host
            session_host_id = request.session.get("host")
            try:
                session_host_id = int(session_host_id)
                session_host = hosts.filter(id=session_host_id).first()
            except:
                session_host = None

            if session_host:
                request.current_host = session_host
            else:
                request.current_host = hosts.first()
                if hosts:
                    request.session['host'] = hosts.first().id