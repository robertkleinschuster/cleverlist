from django.contrib import admin
from django.utils.html import format_html

from cleverlist.admin import ListActionModelAdmin
from inventory.models import Location, ProductStock, ProductWithStock, MinimumProductStock
from django.db.models import Sum, Count
from django.utils.translation import gettext_lazy as _

from master.admin import FormWithTags, format_tag, TagFilter


class ProductStockInline(admin.StackedInline):
    model = ProductStock
    form = FormWithTags
    extra = 0
    readonly_fields = ['description']


# Register your models here.
@admin.register(Location)
class LocationAdmin(ListActionModelAdmin):
    pass
    form = FormWithTags
    inlines = [ProductStockInline]
    list_display = ('name', 'num_products', 'display_tags')
    search_fields = ['name']
    list_filter = [('tags', TagFilter)]

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(format_tag(tag) for tag in tags))

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('tags')
        queryset = queryset.annotate(
            num_products=Count('productstock__product', distinct=True)
        )
        return queryset

    @admin.display(description=_('Number of products'))
    def num_products(self, obj):
        return obj.num_products


@admin.register(ProductWithStock)
class ProductWithStockAdmin(ListActionModelAdmin):
    pass
    list_display = ['name', 'sum_locations', 'sum_stock', 'display_locations', 'display_tags']
    inlines = [ProductStockInline]
    search_fields = ['name']
    exclude = ['name', 'tags']

    def has_change_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description=_('Locations'))
    def display_locations(self, obj):
        return format_html(
            ', '.join(f'{stock.location} ({stock.stock})' for stock in obj.productstock_set.all())
        )

    @admin.display(description=_('Tags'))
    def display_tags(self, obj):
        tags = []
        for stock in obj.productstock_set.all():
            for tag in stock.tags.all():
                if tag not in tags:
                    tags.append(tag)
        return format_html(' '.join(format_tag(tag) for tag in tags))

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('productstock_set__location')
        queryset = queryset.prefetch_related('productstock_set__tags')
        queryset = queryset.annotate(
            sum_stock=Sum('productstock__stock'),
            sum_locations=Count('productstock__location', distinct=True)
        )
        return queryset

    @admin.display(description=_('Sum of stock'))
    def sum_stock(self, obj):
        return obj.sum_stock

    @admin.display(description=_('Sum of locations'))
    def sum_locations(self, obj):
        return obj.sum_locations


@admin.register(MinimumProductStock)
class MinimumProductStockAdmin(ListActionModelAdmin):
    pass
    form = FormWithTags
    list_display = ('__str__', 'display_tags')
    list_filter = [('tags', TagFilter), 'location']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('tags')
        return queryset

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(format_tag(tag) for tag in tags))
