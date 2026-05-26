from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0007_module_refresh_token'),
    ]

    operations = [
        migrations.CreateModel(
            name='XmppComponent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('host', models.CharField(max_length=255, unique=True)),
                ('port', models.PositiveIntegerField(default=5237)),
                ('ip', models.GenericIPAddressField(default='127.0.0.1')),
                ('password', models.CharField(max_length=255)),
                ('enabled', models.BooleanField(default=True)),
            ],
            options={
                'unique_together': {('ip', 'port')},
            },
        ),
    ]
