from django.contrib import admin
from django.forms.renderers import get_default_renderer
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import helpers
from django.contrib.admin.views.main import ChangeList
from django.utils.safestring import mark_safe


class AdminSite(admin.AdminSite):
    site_header = 'CleverList'
    site_title = 'CleverList'
    index_title = _('Home')
    site_url = None
    empty_value_display = _('None')


class ListActionModelAdmin(admin.ModelAdmin):
    list_actions = []

    def get_changelist(self, request, **kwargs):
        return ActionsChangeList


class ActionsChangeList(ChangeList):
    def __init__(self, request, model, list_display, list_display_links, list_filter, date_hierarchy, search_fields,
                 list_select_related, list_per_page, list_max_show_all, list_editable, model_admin, sortable_by,
                 search_help_text):
        self.add_actions(list_display, request, model_admin)
        super().__init__(request, model, list_display, list_display_links, list_filter, date_hierarchy, search_fields,
                         list_select_related, list_per_page, list_max_show_all, list_editable, model_admin, sortable_by,
                         search_help_text)

    def add_actions(self, list_display: list, request, model_admin):
        if isinstance(model_admin.list_actions, list):
            actions = []
            action_choices = model_admin.get_action_choices(request, [])
            for action, description in action_choices:
                if action in model_admin.list_actions:
                    actions.append((action, description))

            if len(actions) > 0:
                @admin.display(description='')
                def list_actions(obj):
                    renderer = get_default_renderer()
                    return mark_safe(renderer.render('list_actions.html', {
                        'actions': actions,
                        'checkbox_value': obj.pk,
                        'checkbox_name': helpers.ACTION_CHECKBOX_NAME
                    }))

                list_display.append(list_actions)
