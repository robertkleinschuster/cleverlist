from django.contrib import admin

from shopping.models import List, Item
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

class ItemInline(admin.TabularInline):
    model = Item
    extra = 0  # Number of empty inline forms to display


# Register your models here.
@admin.register(List)
class ListAdmin(admin.ModelAdmin):
    pass
    search_fields = ['name']
    inlines = [ItemInline]
    list_display = ['name', 'num_items']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(num_items=Count('item'))
        return queryset

    @admin.display(description=_('Number of items'))
    def num_items(self, obj):
        return obj.num_items
