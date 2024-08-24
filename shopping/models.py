from uuid import uuid4

from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from master.models import Product, Tag


# Create your models here.
class List(models.Model):
    pass
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_('Tags'))

    class Meta:
        verbose_name = _('Shopping List')
        verbose_name_plural = _('Shopping Lists')

    def __str__(self):
        return self.name


class Item(models.Model):
    pass
    uuid = models.UUIDField(default=uuid4, editable=False, unique=True)
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, null=True, blank=True, verbose_name=_('Product'))
    name = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('Name'))
    quantity = models.IntegerField(default=1, verbose_name=_('Quantity'))
    list = models.ForeignKey(List, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Shopping List'))
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_('Tags'))
    in_cart = models.BooleanField(default=False, verbose_name=_('In-Cart'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    class Meta:
        verbose_name = _('Shopping Item')
        verbose_name_plural = _('Shopping Items')

    def __str__(self):
        product_name = self.product.name if self.product else _('without product')
        if self.name:
            product_name = self.name
        return f"{self.quantity} x {product_name}"

    def save(self, *args, **kwargs):
        if not self.name and self.product:
            self.name = self.product.name
        super().save(*args, **kwargs)


@receiver(post_save, sender=Item)
def add_default_tags(sender, instance, created, **kwargs):
    if created:
        tags = list(instance.tags.all())
        if instance.product:
            for tag in instance.product.tags.all():
                if tag not in tags:
                    tags.append(tag)
        if instance.list:
            for tag in instance.list.tags.all():
                if tag not in tags:
                    tags.append(tag)
        if instance.product and instance.product.minimumproductstock_set:
            for minstock in instance.product.minimumproductstock_set.all():
                for tag in minstock.tags.all():
                    if tag not in tags:
                        tags.append(tag)
        if len(tags) > 0 and (instance.list or instance.product):
            transaction.on_commit(lambda: instance.tags.add(*tags))
