from django.contrib import admin
from django.utils.html import format_html
from django import forms

from todo.models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = '__all__'
        widgets = {
            'tags': forms.CheckboxSelectMultiple(),
        }


# Register your models here.
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    pass
    form = TaskForm
    list_display = ['name', 'display_tags']
    list_filter = [('tags', admin.RelatedOnlyFieldListFilter)]

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(str(tag) for tag in tags))
