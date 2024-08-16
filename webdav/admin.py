from django.contrib import admin
from webdav.models import *
from webdav.storage import FSStorage


class PropInline(admin.TabularInline):
    fields = ['resource', 'name', 'value']
    extra = 0
    model = Prop


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'displayname', 'user')
    readonly_fields = ['uuid', 'file']
    inlines = [PropInline]

    filter_horizontal = ['groups']

    storage = FSStorage()

    def file(self, obj):
        if obj.collection is False and obj.content_type == 'text/calendar; charset=utf-8':
            if not self.storage.exists(obj):
                return 'missing'

            return self.storage.retrieve_string(obj)
        return ''


admin.site.register(Prop)
