# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0002_moduleserverconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='moduleserverconfig',
            name='replace',
            field=models.TextField(blank=True, default=''),
        ),
    ]
