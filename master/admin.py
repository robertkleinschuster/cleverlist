from django.contrib import admin
from django import forms
from django.utils.html import format_html

from master.models import Product, Tag


# Register your models here.
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    pass
    search_fields = ['name']


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = '__all__'
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
        }


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass
    form = TagForm

    list_display = ('display_name', 'description')

    @admin.display(description='Tags')
    def display_name(self, obj):
        return format_html(
            f'<span style="background-color: {obj.color}; color: #000; padding: 2px 5px; border-radius: 5px;">'
            f'{obj.name}'
            f'</span>'
        )
