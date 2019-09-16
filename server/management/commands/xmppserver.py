from django.core.management.base import BaseCommand
from server.utils import stop_ejabberd, start_ejabberd, restart_ejabberd, is_ejabberd_running


class Command(BaseCommand):
    help = 'XMPP server management'

    def handle(self, *args, **options):
        if options['stop']:
            stop_ejabberd(change_state=False)
        elif options['start']:
            start_ejabberd()
        elif options['restart']:
            restart_ejabberd()
        elif options['status']:
            if is_ejabberd_running():
                print('XMPP server running')
            else:
                print('XMPP server stopped')
        else:
            print('Enter command')

    def add_arguments(self, parser):
        parser.add_argument(
            '--stop',
            action='store_true',
            default=False,
            help='XMPP server stop'
        )
        parser.add_argument(
            '--start',
            action='store_true',
            default=False,
            help='XMPP server start'
        )
        parser.add_argument(
            '--restart',
            action='store_true',
            default=False,
            help='XMPP server restart'
        )
        parser.add_argument(
            '--status',
            action='store_true',
            default=False,
            help='XMPP server status'
        )
