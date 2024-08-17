from django.contrib import admin
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from cleverlist.admin import ListActionModelAdmin
from master.admin import format_tag, TagFilter
from todo.models import Task, PendingTask


@admin.action(description=_("Mark task as done"))
def mark_done(modeladmin, request, queryset: QuerySet):
    task = queryset.get()
    task.done = timezone.now()
    task.save()


@admin.action(description=_("Mark task as pending"))
def mark_pending(modeladmin, request, queryset):
    task = queryset.get()
    task.done = None
    task.save()


# Register your models here.
@admin.register(Task)
class TaskAdmin(ListActionModelAdmin):
    pass
    list_display = ['name', 'display_tags', 'deadline', 'done']
    list_filter = [('tags', TagFilter), 'done']
    actions = [mark_done, mark_pending]
    list_actions = ['mark_done', 'mark_pending']
    autocomplete_fields = ['tags', 'shoppinglist']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('tags')
        return queryset

    @admin.display(description=_('Tags'))
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(format_tag(tag) for tag in tags))


@admin.register(PendingTask)
class PendingTaskAdmin(TaskAdmin):
    pass
    list_filter = [('tags', TagFilter), 'deadline']
