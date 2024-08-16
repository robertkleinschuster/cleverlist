"""
URL configuration for cleverlist project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path

from webdav.base import WebDAV
from webdav.addressbook import CardDAV
from webdav.calendar import CalDAV
from webdav.wellknown import WellKnownDAV

urlpatterns = [
    re_path(r'^principals/(\w+)/(.*)', WebDAV.as_view(root='storage')),
    re_path(r'^storage/(\w+)/(.*)', WebDAV.as_view(root='storage')),
    re_path(r'^addressbook/(\w+)/(.*)', CardDAV.as_view(root='addressbook001')),
    re_path(r'^calendars/(\w+)/(.*)', CalDAV.as_view(root='calendars')),
    re_path(r'^.well[-_]?known/caldav/?$',
        WellKnownDAV.as_view(root='calendars')),
    re_path(r'^.well[-_]?known/carddav/?$',
        WellKnownDAV.as_view(root='addressbook001')),

    path('', admin.site.urls),
]
