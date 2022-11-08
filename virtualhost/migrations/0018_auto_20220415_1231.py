# Generated by Django 2.2.9 on 2022-04-15 07:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('virtualhost', '0017_auto_20210209_0554'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='expires',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]