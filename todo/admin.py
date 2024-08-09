from django.contrib import admin
from django.utils.html import format_html

from master.admin import FormWithTags, format_tag, TagFilter
from todo.models import Task


# Register your models here.
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    pass
    form = FormWithTags
    list_display = ['name', 'display_tags']
    list_filter = [('tags', TagFilter)]

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(format_tag(tag) for tag in tags))
