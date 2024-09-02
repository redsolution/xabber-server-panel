from django.db import models
import json
from xabber_server_panel.certificates.models import Certificate


class VirtualHost(models.Model):
    name = models.CharField(
        max_length=256,
        unique=True
    )
    srv_records = models.BooleanField(default=False)
    cert_records = models.BooleanField(default=False)
    issue_cert = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def certificate(self):
        cert = Certificate.objects.filter(domain=self.name).first()
        return cert

    @property
    def cert_errors(self):
        errors = []
        if not self.cert_records:
            errors += ['- DNS records for the certificates are missing.']

        if self.certificate:
            if self.certificate.status == 2:
                errors += ['- ' + self.certificate.reason]
        else:
            errors += ['- The certificate has not been uploaded.']

        return errors


class LDAPSettings(models.Model):
    ENCRYPT_CHOICES = (
        ('none', 'none'),
        ('tls', 'tls')
    )

    TLS_VERIFY_CHOICES = (
        ('false', 'false'),
        ('soft', 'soft'),
        ('hard', 'hard'),
    )

    DEFER_ALIASES_CHOICES = (
        ('never', 'never'),
        ('always', 'always'),
        ('finding', 'finding'),
        ('searching', 'searching'),
    )

    encrypt = models.CharField(
        max_length=10,
        choices=ENCRYPT_CHOICES,
        null=True, blank=True
    )
    tls_verify = models.CharField(
        max_length=10,
        choices=TLS_VERIFY_CHOICES,
        null=True, blank=True
    )
    tls_cacertfile = models.CharField(
        max_length=100,
        null=True, blank=True
    )
    tls_depth = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
    port = models.PositiveSmallIntegerField(
        default=389
    )
    rootdn = models.CharField(
        max_length=100,
        null=True, blank=True
    )
    password = models.CharField(
        max_length=50,
        null=True, blank=True
    )
    deref_aliases = models.CharField(
        max_length=100,
        choices=DEFER_ALIASES_CHOICES,
        null=True, blank=True
    )
    base = models.CharField(
        max_length=100
    )
    uids = models.CharField(
        max_length=256,
        null=True, blank=True
    )
    filter = models.CharField(
        max_length=256,
        null=True, blank=True
    )
    dn_filter = models.CharField(
        max_length=256,
        null=True, blank=True
    )
    host = models.ForeignKey(
        VirtualHost,
        on_delete=models.CASCADE,
        related_name='ldap_settings'
    )
    enabled = models.BooleanField(
        default=False
    )

    def __str__(self):
        return 'LDAP Settings %s' % self.host.name


class LDAPServer(models.Model):
    server = models.CharField(max_length=50)
    settings = models.ForeignKey(
        LDAPSettings,
        on_delete=models.CASCADE,
        related_name='servers'
    )

    def __str__(self):
        return 'LDAP Settings {}'.format(self.server)


class RootPage(models.Model):
    module = models.CharField(
        max_length=100,
        default="home"
    )

    def __str__(self):
        return self.module


class Module(models.Model):

    name = models.CharField(
        max_length=30
    )
    verbose_name = models.TextField(
        blank=True,
        null=True
    )
    version = models.CharField(
        max_length=20
    )
    files = models.TextField(
        blank=True,
        null=True
    )
    root_page = models.BooleanField(
        default=False
    )
    global_module = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.name


class ModuleSettings(models.Model):

    """
        Module settings for modules_config.yml
    """

    host = models.CharField(
        max_length=255,
    )
    module = models.CharField(
        max_length=255,
    )
    options = models.TextField()

    def set_options(self, options_dict):
        try:
            self.options = json.dumps(options_dict)
        except:
            pass

    def get_options(self):
        try:
            return json.loads(self.options)
        except:
            return {}

    class Meta:
        unique_together = ('host', 'module')

    def __str__(self):
        return '%s - %s' % (self.host, self.module)


class DiscoUrls(models.Model):

    """
        Add "items" option list for mod_disco_urls in config
        Items dict format:
            {
                'example.com': {
                    "mediagallery": "https://gallery.clandestino.chat/api/"
                },
                'global': {
                    "purchases:apple:v1": "https://chat.clandestino.chat/admin/modules/subscriptions/api/v1/"
                }
            }
    """
    module_name = models.CharField(
        max_length=255
    )
    host = models.CharField(
        max_length=255,
    )
    items = models.TextField()

    def set_items(self, items_dict: dict):
        try:
            self.items = json.dumps(items_dict)
        except:
            pass

    def get_items(self):
        try:
            return json.loads(self.items)
        except:
            return {}


class AddSettings(models.Model):
    """
        Model for additional dynamic settings.
        Used in base_config for example.
    """

    module_name = models.CharField(
        max_length=255
    )
    key = models.CharField(
        max_length=255,
        unique=True
    )
    value = models.TextField()


def check_vhost(vhost):
    return VirtualHost.objects.filter(name=vhost).exists() or vhost == "global"


class BaseXmppModule(models.Model):

    class Meta:
        managed = False

    def __init__(self, vhost, name, module_options):
        self.vhost = vhost
        self.name = name
        self.module_options = module_options
        if not check_vhost(self.vhost):
            raise ValueError("Virtualhost doesn`t exist")
        if not isinstance(self.module_options, dict):
            raise ValueError("Module options must be a dictionary")

    def get_config(self):
        return {
            "type": "module",
            "vhost": self.vhost,
            "name": self.name,
            "module_options": self.module_options
        }

    def __str__(self):
        return self.name


class BaseXmppOption(models.Model):
    class Meta:
        managed = False

    def __init__(self, vhost, name, value):
        self.vhost = vhost
        self.name = name
        self.value = value
        if not check_vhost(self.vhost):
            raise ValueError("Virtualhost doesn`t exist")
        if isinstance(value, dict):
            raise ValueError("Value must not be a dictionary")

    def get_config(self):
        return {
            "type": "option",
            "vhost": self.vhost,
            "name": self.name,
            "value": self.value
        }

    def __str__(self):
        return self.name


class BaseModuleConfig(models.Model):
    GLOBAL_HOST_NAME = "global"

    class Meta:
        managed = False

    virtual_host = models.CharField(
        max_length=255,
        verbose_name="Related virtual host",
        blank=False,
        null=False
    )