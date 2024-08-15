from django.contrib import admin
from django.contrib.admin.utils import display_for_field
from django.utils import timezone
from django.utils.html import format_html

from cleverlist.admin import ListActionModelAdmin
from inventory.models import Location, ProductStock, ProductWithStock, MinimumProductStock
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from master.admin import format_tag, TagFilter
from shopping.models import Item


@admin.action(description=_('Add Shopping Item'))
def add_shopping_item(modeladmin, request, queryset):
    existing_item_dict = {}

    for existing_item in Item.objects.values('id', 'product_id', 'list_id', 'quantity').all():
        if existing_item_dict.get(existing_item['product_id']):
            existing_item_dict.get(existing_item['product_id'])['total_quantity'] += existing_item['quantity']
        else:
            existing_item_dict[existing_item['product_id']] = existing_item
            existing_item_dict[existing_item['product_id']]['total_quantity'] = existing_item['quantity']

    for product in queryset.all():
        item = Item(
            product=product,
            name=product.name,
            quantity=product.stock_needed
        )

        existing_item = existing_item_dict.get(product.pk)
        if existing_item:
            item.quantity -= existing_item['total_quantity']
            item.quantity += existing_item['quantity']
            item.pk = existing_item['id']

        if item.quantity > 0:
            item.save()


class ProductStockInline(admin.StackedInline):
    model = ProductStock
    extra = 0
    readonly_fields = ['update_info']

    fields = ['stock', 'product', 'location', 'tags', 'update_info']
    autocomplete_fields = ['product', 'location', 'tags']

    @admin.display(description=_('Updated at'))
    def update_info(self, obj: ProductStock):
        updated_at = display_for_field(
            timezone.localtime(obj.updated_at), obj._meta.get_field('updated_at'), self.admin_site
        )

        if obj.update_reason:
            return f'{updated_at}: {obj.update_reason}'

        return updated_at


class MinimumProductStockInline(admin.StackedInline):
    pass
    model = MinimumProductStock
    extra = 0
    autocomplete_fields = ['product', 'location', 'tags']


# Register your models here.
@admin.register(Location)
class LocationAdmin(ListActionModelAdmin):
    pass
    list_display = ('name', 'num_products', 'display_tags')
    search_fields = ['name']
    list_filter = [('tags', TagFilter)]
    autocomplete_fields = ['tags']

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
    list_display = ['name', 'stock', 'minimum_stock', 'stock_needed', 'display_locations', 'display_tags']
    inlines = [ProductStockInline, MinimumProductStockInline]
    search_fields = ['name']
    exclude = ['name', 'tags']
    list_filter = [('productstock__tags', TagFilter)]
    actions = [add_shopping_item]
    list_actions = ['add_shopping_item']

    def has_change_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description=_('Product Stock'))
    def stock(self, obj):
        return obj.stock

    @admin.display(description=_('Minimum Product Stock'))
    def minimum_stock(self, obj):
        return obj.minimum_stock

    @admin.display(description=_('Stock Needed'))
    def stock_needed(self, obj):
        if obj.stock_needed > 0:
            return format_html('<span style="color: red">{}</span>', obj.stock_needed)
        return format_html('<span style="color: green">{}</span>', obj.stock_needed)

    @admin.display(description=_('Locations'))
    def display_locations(self, obj):
        location_stock_dict = {}
        for stock in obj.productstock_set.all():
            if stock.location:
                location = str(stock.location)
            else:
                location = _('No location')

            if location_stock_dict.get(location):
                location_stock_dict[location] += stock.stock
            else:
                location_stock_dict[location] = stock.stock

        return format_html(
            ', '.join(f'{location} ({stock})' for location, stock in location_stock_dict.items())
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
        return queryset
