from django.db import models
from django.utils.translation import gettext_lazy as _

from master.models import Tag


# Create your models here.
class Task(models.Model):
    pass
    name = models.CharField(max_length=100)
    deadline = models.DateTimeField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Task')
        verbose_name_plural = _('Tasks')
