from uuid import uuid4
from django.db import models
from django.utils.translation import gettext_lazy as _

from master.models import Tag
from shopping.models import List


# Create your models here.
class Task(models.Model):
    pass
    uuid = models.UUIDField(default=uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    deadline = models.DateTimeField(null=True, blank=True, verbose_name=_('Deadline'))
    done = models.DateTimeField(null=True, blank=True, editable=False, verbose_name=_('Done'))
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_('Tags'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Task')
        verbose_name_plural = _('Tasks')


class PendingTaskManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(done=None)


class PendingTask(Task):
    pass

    default_manager = PendingTaskManager()

    class Meta:
        proxy = True
        verbose_name = _('Pending Task')
        verbose_name_plural = _('Pending Tasks')
