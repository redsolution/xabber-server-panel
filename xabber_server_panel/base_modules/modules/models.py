from django.db import models


class XServicesToken(models.Model):

    token = models.TextField(unique=True)
    expires = models.DateTimeField()
    jid = models.EmailField(unique=True)


class ModuleServerConfig(models.Model):
    module = models.ForeignKey(
        'config.Module',
        on_delete=models.CASCADE,
        related_name='server_configs'
    )
    name = models.CharField(max_length=255)
    options = models.TextField(blank=True, default='{}')
    replace = models.TextField(blank=True, default='')
    hosts = models.TextField(blank=True, default='')

    def set_options(self, options):
        self.options = options.strip()

    def get_options(self):
        return self.options.strip()

    def set_replace(self, modules):
        self.replace = ','.join(self.normalize_replace(modules))

    def get_replace(self):
        return self.normalize_replace(self.replace)

    def set_hosts(self, hosts):
        self.hosts = ','.join(self.normalize_list(hosts))

    def get_hosts(self):
        return self.normalize_list(self.hosts)

    @staticmethod
    def normalize_replace(modules):
        return ModuleServerConfig.normalize_list(modules)

    @staticmethod
    def normalize_list(items):
        if not items:
            return []

        if isinstance(items, str):
            items = items.split(',')

        result = []
        for item in items:
            if not item:
                continue

            item = item.strip()
            if item and item not in result:
                result.append(item)

        return result

    class Meta:
        unique_together = ('module', 'name')

    def __str__(self):
        return '%s - %s' % (self.module.name, self.name)
