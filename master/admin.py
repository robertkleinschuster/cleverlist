import operator

from django.contrib import admin
from django import forms
from django.contrib.admin.utils import get_model_from_relation
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from cleverlist.admin import ListActionModelAdmin
from master.models import Product, Tag


def format_tag(tag: Tag) -> str:
    return format_html(
        f'<span title="{tag.description}" class="tag" style="background-color: {tag.color}">{tag.name}</span>'
    )


class TagFilter(admin.RelatedFieldListFilter):
    def choices(self, changelist):
        add_facets = changelist.add_facets
        facet_counts = self.get_facet_queryset(changelist) if add_facets else None
        yield {
            "selected": self.lookup_val is None and not self.lookup_val_isnull,
            "query_string": changelist.get_query_string(
                remove=[self.lookup_kwarg, self.lookup_kwarg_isnull]
            ),
            "display": _("All"),
        }
        for pk_val, val in self.lookup_choices:
            if add_facets:
                count = facet_counts[f"{pk_val}__c"]
                val = mark_safe(f"{val} ({count})")
            yield {
                "selected": self.lookup_val is not None
                            and str(pk_val) in self.lookup_val,
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg: pk_val}, [self.lookup_kwarg_isnull]
                ),
                "display": val,
            }

        empty_title = self.empty_value_display
        if self.include_empty_choice:
            if add_facets:
                count = facet_counts["__c"]
                empty_title = mark_safe(f"{empty_title} ({count})")
            yield {
                "selected": bool(self.lookup_val_isnull),
                "query_string": changelist.get_query_string(
                    {self.lookup_kwarg_isnull: "True"}, [self.lookup_kwarg]
                ),
                "display": empty_title,
            }

    def field_choices(self, field, request, model_admin):
        pk_qs = (
            model_admin.get_queryset(request)
            .distinct()
            .values_list("%s__pk" % self.field_path, flat=True)
        )

        model = get_model_from_relation(field)
        qs = model.objects.complex_filter({"pk__in": pk_qs})
        ordering = self.field_admin_ordering(field, request, model_admin)
        qs = qs.order_by(*ordering)

        choice_func = operator.attrgetter(
            field.remote_field.get_related_field().attname
            if hasattr(field.remote_field, "get_related_field")
            else "pk"
        )

        return [
            (choice_func(tag), format_tag(tag)) for tag in qs
        ]


# Register your models here.
@admin.register(Product)
class ProductAdmin(ListActionModelAdmin):
    pass
    list_display = ['name', 'display_tags']
    search_fields = ['name']
    list_filter = [('tags', TagFilter)]
    autocomplete_fields = ['tags']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('tags')
        return queryset

    @admin.display(description='Tags')
    def display_tags(self, obj):
        tags = obj.tags.all()
        return format_html(' '.join(format_tag(tag) for tag in tags))


class TagForm(forms.ModelForm):
    class Meta:
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
        }


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    pass
    form = TagForm
    search_fields = ['name']
    list_display = ('display_name', 'description')

    @admin.display(description='Tags')
    def display_name(self, obj):
        return format_tag(obj)
