from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Tag(models.Model):
    pass
    name = models.CharField(unique=True, max_length=100, verbose_name=_('Name'))
    color = models.CharField(max_length=7, default='#ffffff', verbose_name=_('Color'))
    description = models.TextField(null=True, blank=True, verbose_name=_('Description'))

    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')

    def __str__(self):
        html = f'<span title="{self.description}" class="tag" style="background-color: {self.color};">{self.name}</span>'
        return format_html(html)


class Product(models.Model):
    pass
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_('Tags'))

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')

    def __str__(self):
        return self.name
