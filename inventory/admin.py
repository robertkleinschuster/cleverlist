from django.contrib import admin

from inventory.models import Location, ProductStock
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

class ProductStockInline(admin.TabularInline):
    model = ProductStock
    extra = 0


# Register your models here.
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    pass
    inlines = [ProductStockInline]
    list_display = ('name', 'num_products')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(num_products=Count('productstock__product', distinct=True))
        return queryset

    @admin.display(description=_('Number of products'))
    def num_products(self, obj):
        return obj.num_products

@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    pass
    list_display = ('product', 'location', 'stock')