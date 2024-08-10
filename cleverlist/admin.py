from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.contrib.admin import helpers
from django.contrib.admin.views.main import ChangeList
from django.utils.safestring import mark_safe
from widgets import ListActionButton


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
            buttons = []
            action_choices = model_admin.get_action_choices(request, [])
            for action, description in action_choices:
                for list_action in model_admin.list_actions:
                    if isinstance(list_action, tuple):
                        list_action, action_button_class = list_action
                    else:
                        list_action = list_action
                        action_button_class = ListActionButton
                    if list_action == action:
                        button = action_button_class(attrs={
                            'label': description,
                            'data-checkbox-name': helpers.ACTION_CHECKBOX_NAME
                        })
                        buttons.append((action, button))

            if len(buttons) > 0:
                @admin.display(description='')
                def list_actions(obj):
                    content = mark_safe(' '.join([
                        btn.render('action', act, {
                            'data-checkbox-value': obj.pk,
                        }) for act, btn in buttons
                    ]))

                    return format_html(
                        '<input type="checkbox" name="list-actions" id="list-actions-{}"/> <label for="list-actions-{}">{}</label><div>{}</div>',
                        obj.pk,
                        obj.pk,
                        _("Actions"),
                        content
                    )

                list_display.append(list_actions)
