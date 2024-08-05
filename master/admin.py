from django.contrib import admin

from master.models import Product


# Register your models here.
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    pass
    search_fields = ['name']
