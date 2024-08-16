from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WebDAVConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webdav'
    verbose_name = _('WebDAV')
