from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0008_xmppcomponent'),
    ]

    operations = [
        migrations.AddField(
            model_name='xmppcomponent',
            name='privileged',
            field=models.BooleanField(default=False),
        ),
    ]
