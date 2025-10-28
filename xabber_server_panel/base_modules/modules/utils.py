from django.shortcuts import reverse

from xabber_server_panel.base_modules.config.models import Module
from xabber_server_panel.utils import check_versions


def get_modules_data(available_modules):
    
    installed_modules = {module.name: module for module in Module.objects.all()}

    modules_data = []
    processed_modules = set()
    grouped_available_modules = {}

    # Handle installed modules
    for module_name, installed_module in installed_modules.items():
        available_module_data = available_modules.get(module_name, {})
        module_info = {
            'name': module_name,
            'display_name': installed_module.verbose_name or module_name,
            'track': installed_module.track,
            'version': installed_module.version,
            'root_page': installed_module.root_page,
            'global_module': installed_module.global_module,
            'custom': installed_module.custom,
            'created_installed': installed_module.created,
            'installed': True,
            'description': installed_module.description,
            'update_links': check_module_versions(installed_module, available_module_data),
        }
        modules_data.append(module_info)
        processed_modules.add(module_name)

    # Group available modules by name and version
    for module_name, tracks in available_modules.items():
        for track, module in tracks.items():
            key = (module_name, module.get('release'))

            if key not in grouped_available_modules:
                grouped_available_modules[key] = {
                    'name': module_name,
                    'display_name': module.get('display_name', module_name),
                    'version': module.get('release'),
                    'created': module.get('created'),
                    'description': module.get('description'),
                    'tracks': [],
                    'installed': False,
                    'update_links': {},
                }

            grouped_available_modules[key]['tracks'].append(track)

    # Add available modules excluding installed modules
    for module_info in grouped_available_modules.values():
        if module_info['name'] not in processed_modules:
            modules_data.append(module_info)

    # Sort by installed status
    modules_data.sort(key=lambda x: not x['installed'])

    return modules_data


def get_available_modules(available_modules):

    installed_modules = Module.objects.all().values_list('name', flat=True)

    modules_data = []
    processed_modules = set()
    grouped_available_modules = {}

    # Group available modules by name and version
    for module_name, tracks in available_modules.items():
        if module_name not in installed_modules:
            for track, module in tracks.items():
                key = (module_name, module.get('release'))

                if key not in grouped_available_modules:
                    grouped_available_modules[key] = {
                        'name': module_name,
                        'display_name': module.get('display_name', module_name),
                        'version': module.get('release'),
                        'created': module.get('created'),
                        'description': module.get('description'),
                        'tracks': [],
                        'update_links': {},
                    }

                grouped_available_modules[key]['tracks'].append(track)

    # Add available modules excluding installed modules
    for module_info in grouped_available_modules.values():
        if module_info['name'] not in processed_modules:
            modules_data.append(module_info)

    return modules_data


def check_module_versions(module: Module, available_module_data: dict):
    """ Check available updates and return links list """
    result = {}

    if isinstance(module, Module) and isinstance(available_module_data, dict):
        new_module_free = available_module_data.get('free')
        new_module_paid = available_module_data.get('paid')

        if not module.custom:
            if module.track == 'free':
                if new_module_free:
                    if check_versions(module.version, new_module_free.get('release')).get('success'):
                        result['upgrade'] = reverse('modules:upload_module',
                                                    kwargs={'module_name': module.name, 'track': 'free'})
                if new_module_paid:
                    if check_versions(module.version, new_module_paid.get('release'), equals_ok=True).get(
                            'success'):
                        result['buy'] = reverse('modules:upload_module',
                                                kwargs={'module_name': module.name, 'track': 'paid'})
            elif module.track == 'paid':
                if new_module_paid:
                    if check_versions(module.version, new_module_paid.get('release')).get('success'):
                        result['upgrade'] = reverse('modules:upload_module',
                                                    kwargs={'module_name': module.name, 'track': 'paid'})

    return result