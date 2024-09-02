from django.db import models


class Certificate(models.Model):

    STATUS_CHOICES = [
        (0, 'Success'),
        (1, 'Pending'),
        (2, 'Error'),
    ]

    name = models.CharField(
        max_length=255,
        unique=True
    )
    domain = models.TextField()
    expiration_date = models.DateTimeField(
        blank=True,
        null=True
    )
    status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=0
    )
    reason = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.domain