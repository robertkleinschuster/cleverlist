from django import forms
from django.contrib import admin
from django.utils.html import format_html

from inventory.models import Location, ProductStock, ProductWithStock
from django.db.models import Sum, Count
from django.utils.translation import gettext_lazy as _


class ProductStockForm(forms.ModelForm):
    class Meta:
        model = ProductStock
        fields = '__all__'
        widgets = {
            'tags': forms.CheckboxSelectMultiple(),
        }


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = '__all__'
        widgets = {
            'tags': forms.CheckboxSelectMultiple(),
        }


class ProductStockInline(admin.StackedInline):
    model = ProductStock
    form = ProductStockForm
    extra = 0


# Register your models here.
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    pass
    form = LocationForm
    inlines = [ProductStockInline]
    list_display = ('name', 'num_products', 'display_tags')
    search_fields = ['name']
    list_filter = [('tags', admin.RelatedOnlyFieldListFilter)]

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(str(tag) for tag in tags))

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
    form = ProductStockForm
    list_display = ('name', 'sum_stock', 'display_tags')
    inlines = [ProductStockInline]
    search_fields = ['name']
    list_filter = [('tags', admin.RelatedOnlyFieldListFilter)]

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(str(tag) for tag in tags))

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            sum_stock=Sum('productstock__stock'),
        )
        return queryset

    @admin.display(description=_('Sum of stock'))
    def sum_stock(self, obj):
        return obj.sum_stock
