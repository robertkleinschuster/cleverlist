from django.db import models
from master.models import Product, Tag
from django.utils.translation import gettext_lazy as _


# Create your models here.

class Location(models.Model):
    pass
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_('Tags'))

    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")

    def __str__(self):
        return self.name


class ProductStock(models.Model):
    pass
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, verbose_name=_('Product'))
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.RESTRICT, verbose_name=_('Location'))
    stock = models.IntegerField(default=0, verbose_name=_('Stock'))
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_('Tags'))
    description = models.TextField(null=True, blank=True, verbose_name=_('Description'))

    def __str__(self):
        return f"{self.product.name}"

    class Meta:
        verbose_name = _("Product Stock")
        verbose_name_plural = _("Product Stock")


class ProductWithStock(Product):
    pass

    class Meta:
        verbose_name = _("Product with stock")
        verbose_name_plural = _("Products with stock")
        proxy = True


class MinimumProductStock(models.Model):
    pass
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, verbose_name=_('Product'))
    location = models.ForeignKey(Location, on_delete=models.RESTRICT, verbose_name=_('Location'))
    minimum_stock = models.IntegerField(default=0, verbose_name=_('Minimum Stock'))
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_('Tags'))

    def __str__(self):
        return f"{self.minimum_stock} x {self.product.name} ({self.location.name})"

    class Meta:
        unique_together = ('product', 'location')
        verbose_name = _("Minimum Product Stock")
        verbose_name_plural = _("Minimum Product Stocks")
