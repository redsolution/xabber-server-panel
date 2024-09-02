from django.core.management.base import BaseCommand

from xabber_server_panel.base_modules.config.forms import VirtualHostForm
from xabber_server_panel.base_modules.config.utils import update_ejabberd_config, get_dns_records


class Command(BaseCommand):
    help = 'Create new virtual host'

    def add_arguments(self, parser):
        parser.add_argument('--host', '-H', type=str, required=True)

    def handle(self, *args, **options):
        host = options['host']
        data = {
            'name': host
        }

        # check srv records
        records = get_dns_records(host)
        if not 'error' in records:
            data['srv_records'] = True

        form = VirtualHostForm(data)
        if form.is_valid():
            host = form.save()
            print('Host "%s" created successfully!' % host)

        else:
            print(form.errors)