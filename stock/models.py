from django.db import models

from master.models import Product


# Create your models here.
class ProductStock(models.Model):
    pass
    product = models.ForeignKey(Product, on_delete=models.RESTRICT)
    stock = models.IntegerField(default=0)