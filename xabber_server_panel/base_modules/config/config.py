from xabber_server_panel.base_modules.config.models import BaseXmppModule, ModuleSettings
from xabber_server_panel.base_modules.config.utils import get_mod_disco_urls_items


def get_xmpp_server_config():
    settings = ModuleSettings.objects.all()
    configs = []
    for s in settings:
        # add config
        try:
            config = BaseXmppModule(
                vhost=s.host,
                name=s.module,
                module_options=s.get_options()
            )
            configs += [config]
        except Exception as e:
            print(e)

    # add mod disco urls config
    mod_disco_urls_items = get_mod_disco_urls_items()
    for host, items in mod_disco_urls_items.items():
        try:
            config = BaseXmppModule(
                vhost=host,
                name='mod_disco_urls',
                module_options={
                    'items': [
                        items
                    ]
                }
            )
            configs += [config]
        except Exception as e:
            print(e)

    return configs