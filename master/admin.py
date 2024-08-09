from django.contrib import admin
from django import forms
from django.utils.html import format_html

from master.models import Product, Tag


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'tags': forms.CheckboxSelectMultiple(),
        }


# Register your models here.
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    pass
    form = ProductForm
    list_display = ['name', 'display_tags']
    search_fields = ['name']
    list_filter = [('tags', admin.RelatedOnlyFieldListFilter)]

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(f'<span title="{tag.description}" class="tag" style="background-color: {tag.color}">{tag.name}</span>' for tag in tags))


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
        return str(obj)
