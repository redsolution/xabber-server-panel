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
    def current(cls):
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            return None

    @classmethod
    def is_ldap(cls):
        return cls.current().name == cls.BACKEND_LDAP

    @classmethod
    def is_sql(cls):
        return cls.current().name == cls.BACKEND_SQL


# ldap_servers:
#   - ldap1.example.org
# ldap_port: 389
# ldap_rootdn: "cn=Manager,dc=domain,dc=org"
# ldap_password: "**********"
class LDAPSettings(models.Model):
    port = models.PositiveSmallIntegerField()
    rootdn = models.CharField(max_length=100)
    password = models.CharField(max_length=50)

    def __unicode__(self):
        return 'LDAP Settings'

    @classmethod
    def current(cls):
        try:
            instance = cls.objects.all()[0]
            return {
                "servers":   [o.server for o in LDAPServer.objects.filter(settings=instance)],
                "port":     instance.port,
                "rootdn":   instance.rootdn,
                "password": instance.password
            }
        except IndexError:
            return None

    @classmethod
    def has_saved_settings(cls):
        return True if cls.current() else False


class LDAPServer(models.Model):
    server = models.CharField(max_length=50)
    settings = models.ForeignKey(LDAPSettings)

    def __unicode__(self):
        return self.server
