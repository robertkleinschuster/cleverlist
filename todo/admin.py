from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from cleverlist.admin import ListActionModelAdmin
from master.admin import FormWithTags, format_tag, TagFilter
from todo.models import Task, PendingTask


@admin.action(description=_("Mark task as done"))
def mark_done(modeladmin, request, queryset):
    queryset.update(done=timezone.now())


@admin.action(description=_("Mark task as pending"))
def mark_pending(modeladmin, request, queryset):
    queryset.update(done=None)


# Register your models here.
@admin.register(Task)
@admin.register(PendingTask)
class TaskAdmin(ListActionModelAdmin):
    pass
    form = FormWithTags
    list_display = ['name', 'display_tags', 'done']
    list_filter = [('tags', TagFilter)]
    actions = [mark_done, mark_pending]
    list_actions = ['mark_done', 'mark_pending']

    @admin.display(description=_('Tags'))
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(format_tag(tag) for tag in tags))
