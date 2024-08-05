from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class AdminSite(admin.AdminSite):
    site_header = 'CleverList'
    site_title = 'CleverList'
    index_title = _('Home')
    site_url = None

