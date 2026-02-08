from django.db import models


class Material(models.Model):
    name = models.CharField(max_length=255, unique=True)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def __str__(self) -> str:
        return self.name

