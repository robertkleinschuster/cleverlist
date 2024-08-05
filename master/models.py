from django.db import models
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Product(models.Model):
    pass
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')

    def __str__(self):
        return self.name
