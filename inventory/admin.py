from django.contrib import admin

from inventory.models import Location, ProductStock, ProductWithStock
from django.db.models import Sum, Count
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
    search_fields = ['name']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(num_products=Count('productstock__product', distinct=True))
        return queryset

    @admin.display(description=_('Number of products'))
    def num_products(self, obj):
        return obj.num_products


@admin.register(ProductWithStock)
class ProductWithStockAdmin(admin.ModelAdmin):
    pass
    list_display = ('name', 'sum_stock')
    inlines = [ProductStockInline]
    search_fields = ['name']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            sum_stock=Sum('productstock__stock'),
        )
        return queryset

    @admin.display(description=_('Sum of stock'))
    def sum_stock(self, obj):
        return obj.sum_stock
