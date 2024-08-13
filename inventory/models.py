from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    description = models.TextField(null=True, blank=True, editable=False, verbose_name=_('Description'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))
    update_reason = models.TextField(null=True, blank=True, verbose_name=_('Update reason'))

    def __str__(self):
        return f"{self.product.name}"

    class Meta:
        verbose_name = _("Product Stock")
        verbose_name_plural = _("Product Stock")

    def save(self, *args, **kwargs):
        if self.pk is not None:
            original = ProductStock.objects.get(pk=self.pk)

            if self.update_reason == original.update_reason:
                self.update_reason = ''

        super(ProductStock, self).save(*args, **kwargs)


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
        verbose_name = _("Minimum Product Stock")
        verbose_name_plural = _("Minimum Product Stocks")


@receiver(post_save, sender=MinimumProductStock)
@receiver(post_save, sender=ProductStock)
def add_default_tags(sender, instance, created, **kwargs):
    if created:
        tags = list(instance.tags.all())
        if instance.product:
            for tag in instance.product.tags.all():
                if tag not in tags:
                    tags.append(tag)
        if instance.location:
            for tag in instance.location.tags.all():
                if tag not in tags:
                    tags.append(tag)
        if len(tags) > 0 and (instance.location or instance.product):
            transaction.on_commit(lambda: instance.tags.add(*tags))
