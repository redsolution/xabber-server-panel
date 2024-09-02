from django.db.models.signals import post_save, pre_delete, post_delete, pre_save
from django.dispatch import receiver

from .models import CronJob
from .crontab import Crontab


@receiver(pre_save, sender=CronJob)
def pre_save_cron_job(sender, *args, **kwargs):
    with Crontab() as crontab:
        try:
            crontab.remove_jobs()
        except:
            pass


@receiver(post_save, sender=CronJob)
def post_save_cron_job(sender, instance, created, **kwargs):
    # built in activate/deactivate logic

    post_save.disconnect(post_save_cron_job, sender=CronJob)

    if instance.type == 'built_in_job' and instance.active:
        CronJob.objects.filter(command=instance.command, active=True).exclude(type='built_in_job').update(active=False)
    elif instance.active:
        CronJob.objects.filter(command=instance.command, active=True, type='built_in_job').update(active=False)

    post_save.connect(post_save_cron_job, sender=CronJob)

    # recreate cron jobs
    with Crontab() as crontab:
        crontab.add_jobs()


@receiver(pre_delete, sender=CronJob)
def pre_delete_cron_job(sender, *args, **kwargs):
    with Crontab() as crontab:
        try:
            crontab.remove_jobs()
        except:
            pass


@receiver(post_delete, sender=CronJob)
def post_delete_cron_job(sender, *args, **kwargs):
    with Crontab() as crontab:
        crontab.add_jobs()

