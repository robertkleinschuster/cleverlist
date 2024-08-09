from django import forms
from django.contrib import admin
from django.utils.html import format_html

from shopping.models import List, Item
from django.db.models import Count
from django.utils.translation import gettext_lazy as _


class ListForm(forms.ModelForm):
    class Meta:
        model = List
        fields = '__all__'
        widgets = {
            'tags': forms.CheckboxSelectMultiple(),
        }


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = '__all__'
        widgets = {
            'tags': forms.CheckboxSelectMultiple(),
        }


class ItemInline(admin.StackedInline):
    model = Item
    form = ItemForm
    extra = 0  # Number of empty inline forms to display


# Register your models here.
@admin.register(List)
class ListAdmin(admin.ModelAdmin):
    pass
    form = ListForm
    search_fields = ['name']
    inlines = [ItemInline]
    list_display = ['name', 'num_items', 'display_tags']
    list_filter = [('tags', admin.RelatedOnlyFieldListFilter)]

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(str(tag) for tag in tags))

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(num_items=Count('item'))
        return queryset

    @admin.display(description=_('Number of items'))
    def num_items(self, obj):
        return obj.num_items
