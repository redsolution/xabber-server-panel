from django.db import models


class RegistrationUrl(models.Model):
    host = models.CharField(
        max_length=255
    )
    url = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.host