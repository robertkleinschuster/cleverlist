from django.db import models
import uuid

from django.db.models import F


# Create your models here.
class CalDAVTasklist(models.Model):
    name = models.CharField(max_length=255, default='')
    code = models.CharField(max_length=255, unique=True, null=True, blank=True)
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    etag = models.CharField(max_length=255)
    sync_token = models.IntegerField(default=1)
    last_modified = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk:
            self.sync_token = F('sync_token') + 1
        super().save(*args, **kwargs)
