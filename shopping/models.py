from django.db import models
from django.utils.translation import gettext_lazy as _
from master.models import Product


# Create your models here.
class List(models.Model):
    pass
    name = models.CharField(max_length=100, verbose_name=_('Name'))

    class Meta:
        verbose_name = _('Shopping List')
        verbose_name_plural = _('Shopping Lists')

    def __str__(self):
        return self.name


class Item(models.Model):
    pass
    list = models.ForeignKey(List, on_delete=models.CASCADE, verbose_name=_('Shopping List'))
    name = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('Name'))
    quantity = models.IntegerField(default=1, verbose_name=_('Quantity'))
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, null=True, blank=True, verbose_name=_('Product'))

    class Meta:
        verbose_name = _('Item')
        verbose_name_plural = _('Items')

    def __str__(self):
        product_name = self.product.name if self.product else _('without product')
        return f"{self.quantity} {self.name} in {self.list.name} ({product_name})"

    def save(self, *args, **kwargs):
        if not self.name and self.product:
            self.name = self.product.name
        super().save(*args, **kwargs)
