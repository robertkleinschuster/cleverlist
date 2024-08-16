from django.contrib import admin
from webdav.models import *


class PropInline(admin.TabularInline):
    fields = ['resource', 'name', 'value']
    extra = 0
    model = Prop


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'displayname', 'user')
    inlines = [PropInline]


admin.site.register(Resource, ResourceAdmin)
admin.site.register(Prop)
