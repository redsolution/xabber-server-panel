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

    def set_options(self, options):
        self.options = options.strip()

    def get_options(self):
        return self.options.strip()

    def set_replace(self, modules):
        self.replace = ','.join(self.normalize_replace(modules))

    def get_replace(self):
        return self.normalize_replace(self.replace)

    @staticmethod
    def normalize_replace(modules):
        if not modules:
            return []

        if isinstance(modules, str):
            modules = modules.split(',')

        result = []
        for module in modules:
            if not module:
                continue

            module = module.strip()
            if module and module not in result:
                result.append(module)

        return result

    class Meta:
        unique_together = ('module', 'name')

    def __str__(self):
        return '%s - %s' % (self.module.name, self.name)
