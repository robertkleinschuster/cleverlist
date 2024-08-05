from django.db import models
from django.utils.translation import gettext_lazy as _
from master.models import Product


# Create your models here.
class List(models.Model):
    pass
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = _('Shopping List')
        verbose_name_plural = _('Shopping Lists')

    def __str__(self):
        return self.name


class Item(models.Model):
    pass
    list = models.ForeignKey(List, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=100)
    count = models.IntegerField()
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, null=True, blank=True)

    class Meta:
        verbose_name = _('Item')
        verbose_name_plural = _('Items')

    def __str__(self):
        product_name = self.product.name if self.product else _('without product')
        return f"{self.name} in {self.list.name} ({product_name})"
