from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.ui.themes import DEFAULT_THEME, THEME_CHOICES


class CustomUser(AbstractUser):
    telegram_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Telegram ID",
    )
    theme = models.CharField(
        max_length=32,
        choices=THEME_CHOICES,
        default=DEFAULT_THEME,
        verbose_name="Theme",
    )

    def __str__(self) -> str:
        return self.username
