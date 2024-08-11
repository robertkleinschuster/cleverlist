from django.contrib import admin
from django.utils.html import format_html

from cleverlist.admin import ListActionModelAdmin
from master.admin import FormWithTags, format_tag, TagFilter
from shopping.models import List, Item
from django.db.models import Count
from django.utils.translation import gettext_lazy as _


class ItemInline(admin.StackedInline):
    model = Item
    form = FormWithTags
    extra = 0  # Number of empty inline forms to display


# Register your models here.
@admin.register(List)
class ListAdmin(ListActionModelAdmin):
    pass
    form = FormWithTags
    search_fields = ['name']
    inlines = [ItemInline]
    list_display = ['name', 'num_items', 'display_tags']
    list_filter = [('tags', TagFilter)]

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


@admin.register(Item)
class ItemAdmin(ListActionModelAdmin):
    form = FormWithTags
    search_fields = ['name']
    list_display = ['__str__', 'display_tags', 'list']
    list_filter = [('tags', TagFilter), ('list', admin.RelatedOnlyFieldListFilter)]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('tags')
        return queryset

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(format_tag(tag) for tag in tags))
