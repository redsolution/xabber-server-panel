# Generated by Django 2.2.9 on 2022-05-11 12:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('virtualhost', '0018_auto_20220415_1231'),
        ('registration', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='registrationsettings',
            name='is_enabled',
        ),
        migrations.RemoveField(
            model_name='registrationsettings',
            name='is_enabled_by_key',
        ),
        migrations.AddField(
            model_name='registrationsettings',
            name='status',
            field=models.CharField(default='disabled', max_length=50),
        ),
        migrations.CreateModel(
            name='RegistrationURL',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=150)),
                ('vhost', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='virtualhost.VirtualHost')),
            ],
        ),
    ]