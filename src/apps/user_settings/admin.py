from django.contrib import admin

from apps.user_settings.models import NotificationSetting


@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ("user", "notify_order_created", "notify_order_finished", "notify_order_created_pause")

