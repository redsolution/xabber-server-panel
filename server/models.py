from django.db import models


class ConfigData(models.Model):
    db_host = models.CharField(max_length=256)
    db_name = models.CharField(max_length=256)
    db_user = models.CharField(max_length=256)
    db_user_pass = models.CharField(max_length=256, null=True, blank=True)

    def __unicode__(self):
        return 'Server config'


class AuthBackend(models.Model):
    BACKEND_SQL = 'sql'
    BACKEND_LDAP = 'ldap'

    BACKEND_CHOICES = (
        (BACKEND_SQL, 'SQL'),
        (BACKEND_LDAP, 'LDAP')
    )
    name = models.CharField(max_length=10, choices=BACKEND_CHOICES)
    is_active = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    @classmethod
    def get_data(cls):
        return [o.name for o in cls.objects.filter(is_active=True)]

    @classmethod
    def ldap(cls):
        try:
            return cls.objects.get(name=cls.BACKEND_LDAP)
        except cls.DoesNotExist:
            return None


class LDAPAuth(models.Model):
    ldap_base = models.CharField(max_length=100)
    ldap_uids = models.CharField(max_length=256, null=True, blank=True)
    ldap_filter = models.CharField(max_length=256, null=True, blank=True)
    ldap_dn_filter = models.CharField(max_length=256, null=True, blank=True)

    def __unicode__(self):
        return 'LDAP Auth'

    @classmethod
    def current(cls):
        try:
            return cls.objects.all().first()
        except IndexError:
            return None

    @property
    def uids(self):
        return self.ldapauth_set.all()

    @property
    def data(self):
        return {
            "ldap_uids": self.ldap_uids,
            "ldap_base": self.ldap_base,
            "ldap_filter": self.ldap_filter,
            "ldap_dn_filter": self.ldap_dn_filter
        }

    @classmethod
    def create_or_update(cls, data):
        if cls.current():
            LDAPAuth.objects.all().delete()

        instance = cls.objects.create(**data)
        return instance


# class LDAPAuthUid(models.Model):
#     ldap_uidattr = models.CharField(max_length=100, default='uid')
#     ldap_uidattr_format = models.CharField(max_length=100, default='%u')
#     auth = models.ForeignKey(LDAPAuth)
#
#     def __unicode__(self):
#         return 'LDAP Auth uuid'


class LDAPSettings(models.Model):
    ENCRYPT_NONE = 'none'
    ENCRYPT_TLS = 'tls'
    ENCRYPT_CHOICE = (
        (ENCRYPT_NONE, 'none'),
        (ENCRYPT_TLS, 'tls')
    )

    TLS_VERIFY_FALSE = 'false'
    TLS_VERIFY_SOFT = 'soft'
    TLS_VERIFY_HARD = 'hard'
    TLS_VERIFY_CHOICE = (
        (TLS_VERIFY_FALSE, 'false'),
        (TLS_VERIFY_SOFT, 'soft'),
        (TLS_VERIFY_HARD, 'hard'),
    )

    DEFER_ALIASES_NEVER = 'never'
    DEFER_ALIASES_ALWAYS = 'always'
    DEFER_ALIASES_FINDING = 'finding'
    DEFER_ALIASES_SEARCHING = 'searching'
    DEFER_ALIASES_CHOICE = (
        (DEFER_ALIASES_NEVER, 'never'),
        (DEFER_ALIASES_ALWAYS, 'always'),
        (DEFER_ALIASES_FINDING, 'finding'),
        (DEFER_ALIASES_SEARCHING, 'searching'),
    )

    ldap_encrypt = models.CharField(
        max_length=100, choices=ENCRYPT_CHOICE, null=True, blank=True)
    ldap_tls_verify = models.CharField(
        max_length=100, choices=TLS_VERIFY_CHOICE, null=True, blank=True)
    ldap_tls_cacertfile = models.CharField(
        max_length=100, null=True, blank=True)
    ldap_tls_depth = models.PositiveSmallIntegerField(
        null=True, blank=True)
    ldap_port = models.PositiveSmallIntegerField(default=389)
    ldap_rootdn = models.CharField(
        max_length=100, null=True, blank=True)
    ldap_password = models.CharField(
        max_length=50, null=True, blank=True)
    ldap_deref_aliases = models.CharField(
        max_length=100, choices=DEFER_ALIASES_CHOICE, null=True, blank=True)

    def __unicode__(self):
        return 'LDAP Settings'

    @classmethod
    def current(cls):
        try:
            return cls.objects.all().first()
        except IndexError:
            return None

    @property
    def servers(self):
        return self.ldapsettingsserver_set.all()

    @property
    def data(self):
        return {
            "ldap_servers": self.servers,
            "ldap_port": self.ldap_port,
            "ldap_encrypt": self.ldap_encrypt,
            "ldap_tls_verify": self.ldap_tls_verify,
            "ldap_tls_cacertfile": self.ldap_tls_cacertfile,
            "ldap_tls_depth": self.ldap_tls_depth,
            "ldap_rootdn": self.ldap_rootdn,
            "ldap_password": self.ldap_password,
            "ldap_deref_aliases": self.ldap_deref_aliases
        }

    @classmethod
    def has_saved_settings(cls):
        return True if cls.current() else False

    @classmethod
    def create_or_update(cls, data):
        if cls.current():
            LDAPSettingsServer.objects.all().delete()
            LDAPSettings.objects.all().delete()

        ldap_server_list = data.pop('ldap_server_list')
        instance = cls.objects.create(**data)
        for server in ldap_server_list:
            LDAPSettingsServer.objects.create(server=server, settings=instance)
        return instance


class LDAPSettingsServer(models.Model):
    server = models.CharField(max_length=50)
    settings = models.ForeignKey(LDAPSettings)

    def __unicode__(self):
        return 'LDAP Settings {}'.format(self.server)
