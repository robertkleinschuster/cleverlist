from django.contrib import admin

from shopping.models import List, Item


class ItemInline(admin.TabularInline):
    model = Item
    extra = 0  # Number of empty inline forms to display


# Register your models here.
@admin.register(List)
class ListAdmin(admin.ModelAdmin):
    pass
    search_fields = ['name']
    inlines = [ItemInline]
