from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.user_settings.models import NotificationSetting


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_notification_settings(sender, instance, created, **kwargs):
    if created:
        NotificationSetting.objects.get_or_create(user=instance)

