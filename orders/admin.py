from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Optionally customize admin user fields
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('telegram_id',)}),  # Add telegram_id field
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('telegram_id',)}),  # Add telegram_id field in the add user form
    )