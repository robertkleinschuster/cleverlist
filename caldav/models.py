from django.db import models
import uuid


# Create your models here.
class CalDAVTasklist(models.Model):
    name = models.CharField(max_length=255, default='')
    code = models.CharField(max_length=255, unique=True, null=True, blank=True)
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    etag = models.CharField(max_length=255)
    last_modified = models.DateTimeField(auto_now=True)
