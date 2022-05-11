from .models import RegistrationSettings
from modules_installation.models import BaseXmppModule, BaseXmppOption


def get_xmpp_server_config():
    settings = RegistrationSettings.objects.all()
    configs = []
    for s in settings:
        try:
            if s.status != "DISABLED":
                configs.append(BaseXmppModule(vhost=s.vhost.name, name="mod_register",
                                              module_options={"password_strength": 32,
                                                              "access": "register"}))
            if s.status == "LINK":
                configs.append(BaseXmppModule(vhost=s.vhost.name, name="mod_registration_keys",
                                              module_options={}))
        except Exception as e:
            return e
    return configs
