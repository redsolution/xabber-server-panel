from django.shortcuts import reverse
from django.http import HttpRequest
from django.utils import timezone
from django.contrib import messages

from xabber_server_panel.base_modules.config.models import Module
from xabber_server_panel.base_modules.modules.models import XServicesToken
from xabber_server_panel.utils import check_versions
from xabber_server_panel.api.api import XabberServicesApi

from typing import Iterable


def get_installed_modules(modules):
    installed_modules = {module.name: module for module in Module.objects.all()}

    modules_data = {}
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
            'description': installed_module.description,
            'update_links': check_module_versions(installed_module, available_module_data),
        }
        modules_data[module_name] = module_info
        processed_modules.add(module_name)

    return modules_data


def get_installed_tracks():
    installed_tracks = {}
    installed_modules_query = Module.objects.all()
    for module in installed_modules_query:
        if module.name not in installed_tracks:
            installed_tracks[module.name] = []

        installed_tracks[module.name] += [module.track]

    return installed_tracks


def get_available_modules(available_modules):
    modules_data = []

    # Group available modules by name and version
    for module_name, tracks in available_modules.items():
        modules_data += list(tracks.values())

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


class PluginsPriceCollector:
    def __init__(self, api: XabberServicesApi, groups: Iterable = ('plugin', 'pocket')):
        self.api = api
        self.groups = groups

    def _collect_products(self, group):
        products = []
        page = 1

        while True:
            response = self.api.product_list({
                'group': group,
                'page': page,
            })

            if self.api.errors:
                break

            for product in response.get('results', []):
                products += [product]

            if not response.get('next'):
                break

            page += 1

        return products
    
    def _process_products(self, products):
        processed_products = {}
        pockets = list(
            filter(
                lambda x: x.get('group') == 'pocket', products
            )
        )
        for pocket in pockets:
            plugins = pocket.get('plugins')
            pocket_id = pocket.get('product_id')
            if not plugins:
                continue

            for plugin in plugins:
                plugin_id = plugin.get('product_id')
                processed_products[plugin_id] = {
                    'price_data': None,
                    'subscribe_id': pocket_id
                }

        plugins = list(
            filter(
                lambda x: x.get('group') == 'plugin', products
            )
        )

        for plugin in plugins:
            plugin_id = plugin.get('product_id')
            
            if plugin_id in processed_products:
                continue

            prices = plugin.get('prices')
            if not prices:
                continue

            price_data = prices[0]
            processed_products[plugin_id] = {
                'price_data': price_data,
                'subscribe_id': plugin_id
            }

        return processed_products

    def get_prices(self):
        """
        Collect prices for multiple product groups.
        """

        products = []

        for group in self.groups:
            products += self._collect_products(group)

        processed_products = self._process_products(products)

        return processed_products


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
                        result['upgrade'] = reverse('modules:download_module_free',
                                                    kwargs={'module_name': module.name})
                if new_module_paid:
                    if check_versions(module.version, new_module_paid.get('release'), equals_ok=True).get(
                            'success'):
                        result['buy'] = reverse('modules:download_module_paid',
                                                kwargs={'module_name': module.name})
            elif module.track == 'paid':
                if new_module_paid:
                    if check_versions(module.version, new_module_paid.get('release')).get('success'):
                        result['upgrade'] = reverse('modules:download_module_paid',
                                                    kwargs={'module_name': module.name})

    return result


def request_license_key(request: HttpRequest, add_message=False):
    "Load license key from xabber services API "

    xservices_api = XabberServicesApi(request)
    token = XServicesToken.objects.filter(expires__gt=timezone.now()).first()
    
    if not token:
        return {'success': False, 'error': "Xabber Services Account is not authenticated."}
    
    response = xservices_api.license_key(data={"token": token.token})
    if xservices_api.errors:
        message = "Request license key error. Try to relogin."
        if add_message:
            messages.error(request, message)
        return {'success': False, 'error': message}
    
    key = response.get('license_key')
    services_hash = response.get("services_hash")

    # Check if the key is not empty after stripping
    if not key:
        message = "Request license key error. Try to relogin."
        if add_message:
            messages.error(request, message)
        return {'success': False, 'error': message}

    return {'success': True, 'key': key, "services_hash": services_hash}