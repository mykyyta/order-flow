from django.db import models
from django.utils import timezone


class Material(models.Model):
    name = models.CharField(max_length=255, unique=True)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

