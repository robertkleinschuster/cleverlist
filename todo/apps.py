from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TodoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'todo'
    verbose_name = _('To-Do')
