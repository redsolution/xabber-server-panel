from django.shortcuts import reverse

from xabber_server_panel.base_modules.config.models import Module
from xabber_server_panel.utils import check_versions


# TODO: to remove
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


def get_installed_modules(modules):
    installed_modules = {module.name: module for module in Module.objects.all()}

    modules_data = []
    processed_modules = set()

    # Handle installed modules
    for module_name, installed_module in installed_modules.items():
        available_module_data = modules.get(module_name, {})
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

    return modules_data


def get_available_modules(available_modules):

    installed_modules = {}
    installed_modules_query = Module.objects.all()
    for module in installed_modules_query:
        if module.name not in installed_modules:
            installed_modules[module.name] = []

        installed_modules[module.name] += [module.track]

    modules_data = []

    # Group available modules by name and version
    for module_name, tracks in available_modules.items():
        if module_name not in installed_modules:
            modules_data += list(tracks.values())
        else:
            for track_name, module in tracks.items():
                if track_name not in installed_modules[module_name]:
                    modules_data += [module]

    return modules_data


def get_plugins_prices(xservices_api):
    all_prices = {}
    page = 1

    # collect all pages
    while True:
        # Fetch a page of plugin products
        response = xservices_api.product_list({
            'group': 'plugin',
            'page': page,
        })

        if xservices_api.errors:
            break

        # collect price data from page
        for plugin in response.get('results', []):
            plugin_name = plugin.get('product_id')
            prices = plugin.get('prices', [])

            # skip if plugin has no price
            if not prices:
                continue

            all_prices[plugin_name] = prices

        next_url = response.get('next')
        if not next_url:
            break

        page += 1

    return all_prices


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
                        result['upgrade'] = reverse('modules:download_module',
                                                    kwargs={'module_name': module.name, 'track': 'free'})
                if new_module_paid:
                    if check_versions(module.version, new_module_paid.get('release'), equals_ok=True).get(
                            'success'):
                        result['buy'] = reverse('modules:download_module',
                                                kwargs={'module_name': module.name, 'track': 'paid'})
            elif module.track == 'paid':
                if new_module_paid:
                    if check_versions(module.version, new_module_paid.get('release')).get('success'):
                        result['upgrade'] = reverse('modules:download_module',
                                                    kwargs={'module_name': module.name, 'track': 'paid'})

    return result