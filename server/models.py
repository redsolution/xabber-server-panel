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
    def current_backend(cls):
        try:
            return cls.objects.get(is_active=True).name
        except cls.DoesNotExist:
            return None

    @classmethod
    def is_ldap(cls):
        return cls.current_backend == cls.BACKEND_LDAP

    @classmethod
    def is_sql(cls):
        return cls.current_backend == cls.BACKEND_SQL
