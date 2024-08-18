from django import forms
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from cleverlist.admin import ListActionModelAdmin
from inventory.models import ProductStock, ProductWithStock
from master.admin import format_tag, TagFilter
from shopping.models import List, Item
from django.db.models import Count
from django.utils.translation import gettext_lazy as _


class ItemInline(admin.StackedInline):
    model = Item
    extra = 0  # Number of empty inline forms to display
    autocomplete_fields = ['product', 'list', 'tags']


class ListAdminForm(forms.ModelForm):
    pass

    products_under_stock = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=[],
        label=_('Add products under minimum stock'),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super(ListAdminForm, self).__init__(*args, **kwargs)

        self.fields['products_under_stock'].choices = [
            (item.product.id, str(item)) for item in find_items_under_stock(self.instance)
        ]

    class Meta:
        model = List
        fields = ['name', 'tags', 'products_under_stock']


def find_items_under_stock(shoppinglist: List) -> list:
    existing_item_dict = {}

    for existing_item in Item.objects.values('id', 'product_id', 'list_id', 'quantity').all():
        if existing_item_dict.get(existing_item['product_id']):
            existing_item_dict.get(existing_item['product_id'])['quantity'] += existing_item['quantity']
        else:
            existing_item_dict[existing_item['product_id']] = existing_item

    products = ProductWithStock.default_manager.all()
    for product in products:
        item = Item(
            product=product,
            name=product.name,
            quantity=product.stock_needed,
            list=shoppinglist
        )

        existing_item = existing_item_dict.get(product.pk)
        if existing_item:
            item.quantity -= existing_item['quantity']
            if existing_item['list_id'] == shoppinglist.id:
                item.pk = existing_item['id']

        if item.quantity > 0:
            yield item


# Register your models here.
@admin.register(List)
class ListAdmin(ListActionModelAdmin):
    pass
    form = ListAdminForm
    search_fields = ['name']
    inlines = [ItemInline]
    list_display = ['name', 'num_items', 'display_tags']
    list_filter = [('tags', TagFilter)]
    autocomplete_fields = ['tags']

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(format_tag(tag) for tag in tags))

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('tags')
        queryset = queryset.annotate(num_items=Count('item'))
        return queryset

    @admin.display(description=_('Number of items'))
    def num_items(self, obj):
        return obj.num_items

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        products_to_add = [int(product_id) for product_id in form.cleaned_data['products_under_stock']]
        if len(products_to_add):
            for item in find_items_under_stock(obj):
                if item.product.id in products_to_add:
                    if item.pk:
                        item.quantity += Item.objects.values('quantity').get(pk=item.pk)['quantity']
                    item.save()


@admin.action(description=_("Add to cart"))
def add_to_cart(modeladmin, request, queryset):
    item = queryset.get()
    item.in_cart = True
    item.save()


@admin.action(description=_("Remove from cart"))
def remove_from_cart(modeladmin, request, queryset):
    item = queryset.get()
    item.in_cart = False
    item.save()


@admin.action(description=_("Move to inventory"))
def move_to_inventory(modeladmin, request, queryset):
    items = queryset.select_related('product', 'list').prefetch_related('tags').all()
    for item in items:
        tags = item.tags.all()
        stock_queryset = ProductStock.objects.filter(product=item.product)
        if len(tags):
            stock_queryset = stock_queryset.filter(tags__in=tags).distinct()
            stock_queryset = stock_queryset.annotate(num_tags=Count('tags', distinct=True)).filter(num_tags=len(tags))
        else:
            stock_queryset = stock_queryset.filter(location=None).annotate(num_tags=Count('tags')).filter(num_tags=0)

        stock = stock_queryset.first()

        if item.list:
            update_reason = _('Shopping item “%(item)s” from “%(list)s” added.') % {'list': str(item.list),
                                                                                    'item': str(item)}
        else:
            update_reason = _('Shopping item “%(item)s” added.') % {'item': str(item)}

        if stock:
            stock.stock += item.quantity
            stock.update_reason = update_reason
            stock.save()
        else:
            stock = ProductStock(
                product=item.product,
                stock=item.quantity,
                update_reason=update_reason
            )
            stock.save()
            stock.tags.set(item.tags.all())

        item.delete()


@admin.register(Item)
class ItemAdmin(ListActionModelAdmin):
    search_fields = ['name']
    list_display = ['__str__', 'in_cart', 'display_tags', 'list']
    list_filter = ['in_cart', ('list', admin.RelatedOnlyFieldListFilter), ('tags', TagFilter)]
    actions = [add_to_cart, remove_from_cart, move_to_inventory]
    list_actions = ['add_to_cart', 'remove_from_cart']
    autocomplete_fields = ['product', 'list', 'tags']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('tags')
        return queryset

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(format_tag(tag) for tag in tags))
