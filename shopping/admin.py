from django import forms
from django.contrib import admin
from django.forms import CheckboxSelectMultiple
from django.utils.html import format_html

from cleverlist.admin import ListActionModelAdmin
from inventory.models import MinimumProductStock, ProductStock
from master.admin import FormWithTags, format_tag, TagFilter, TagModelChoiceField
from shopping.models import List, Item
from django.db.models import Count, Sum
from django.utils.translation import gettext_lazy as _


class ItemInline(admin.StackedInline):
    model = Item
    form = FormWithTags
    extra = 0  # Number of empty inline forms to display


class ListAdminForm(forms.ModelForm):
    pass
    add_products_under_minimum_stock = forms.BooleanField(required=False, label=_('Add products under minimum stock'),
                                                          initial=True)

    class Meta:
        model = List
        fields = ['name', 'tags', 'add_products_under_minimum_stock']
        widgets = {
            'tags': CheckboxSelectMultiple,
        }
        field_classes = {
            "tags": TagModelChoiceField,
        }


def find_items_under_stock(obj):
    product_stocks = (ProductStock.objects.values('product')
                      .annotate(total_stock=Sum('stock')))

    minimum_product_stocks = (MinimumProductStock.objects
                              .select_related('product')
                              .annotate(total_minimum_stock=Sum('minimum_stock'))
                              .all())

    product_stock_dict = {ps['product']: ps['total_stock'] for ps in product_stocks}
    existing_item_dict = {item.product.pk: item for item in Item.objects.all()}

    for mps in minimum_product_stocks:
        current_stock = product_stock_dict.get(mps.product.pk, 0)
        stock_needed = mps.minimum_stock - current_stock
        if stock_needed > 0:
            existing_item = existing_item_dict.get(mps.product.pk)
            if existing_item:
                if existing_item.quantity < stock_needed:
                    if existing_item.list_id == obj.id:
                        existing_item.quantity = stock_needed
                        existing_item.save()
                    else:
                        yield Item(
                            product=mps.product,
                            name=mps.product.name,
                            quantity=stock_needed - existing_item.quantity,
                            list=obj,
                        )
            else:
                yield Item(
                    product=mps.product,
                    name=mps.product.name,
                    quantity=stock_needed,
                    list=obj,
                )


# Register your models here.
@admin.register(List)
class ListAdmin(ListActionModelAdmin):
    pass
    form = ListAdminForm
    search_fields = ['name']
    inlines = [ItemInline]
    list_display = ['name', 'num_items', 'display_tags']
    list_filter = [('tags', TagFilter)]

    readonly_fields = ['products_under_stock']

    @admin.display(description=_('Products under stock'))
    def products_under_stock(self, obj):
        return "\n".join([str(item) for item in find_items_under_stock(obj)])

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
        if form.cleaned_data.get('add_products_under_minimum_stock'):
            for item in find_items_under_stock(obj):
                item.save()


@admin.action(description=_("Add to cart"))
def add_to_cart(modeladmin, request, queryset):
    queryset.update(in_cart=True)


@admin.action(description=_("Remove from cart"))
def remove_from_cart(modeladmin, request, queryset):
    queryset.update(in_cart=False)


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
    form = FormWithTags
    search_fields = ['name']
    list_display = ['__str__', 'in_cart', 'list', 'display_tags']
    list_filter = ['in_cart', ('list', admin.RelatedOnlyFieldListFilter), ('tags', TagFilter)]
    actions = [add_to_cart, remove_from_cart, move_to_inventory]
    list_actions = ['add_to_cart', 'remove_from_cart']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('tags')
        return queryset

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(format_tag(tag) for tag in tags))
