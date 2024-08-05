from django.contrib import admin

from stock.models import ProductStock


# Register your models here.
@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    pass