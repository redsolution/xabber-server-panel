from django.core.management.base import BaseCommand

from xabber_server_panel.base_modules.modules.module_installer import ModuleInstaller


class Command(BaseCommand):
    help = 'Install module from provided path.'

    def add_arguments(self, parser):
        parser.add_argument('--path', '-p', type=str, required=True)
        parser.add_argument('--non-custom', '-nc', action='store_false', help="Set this flag to mark the module as non-custom")
        parser.add_argument('--track', '-t', type=str, required=False, default='free')
        parser.add_argument('--description', '-d', type=str, required=False, default='')

    def handle(self, *args, **options):
        path = options['path']
        non_custom = options['non_custom']
        track = options['track']
        description = options['description']

        try:
            with open(path, 'rb') as file:
                module_installer = ModuleInstaller(
                    uploaded_file=file,
                    custom=non_custom,
                    track=track,
                    description=description,
                )
                module_installer.handle_install()
            print('Module installed successfully.')
        except Exception as e:
            print(e)
