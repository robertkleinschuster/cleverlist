from django.urls import path
from . import views

urlpatterns = [
    path('caldav/principal/', views.principal_handler, name='caldav_principal'),
    path('caldav/principal', views.principal_handler),
    path('caldav/home/', views.home_handler, name='caldav_home'),
    path('caldav/home', views.home_handler),
    path('caldav/<str:calendar_id>/', views.propfind, name='caldav_propfind'),
    path('caldav/<str:calendar_id>', views.propfind),
    path('caldav/<str:calendar_id>/<str:event_uid>/', views.get_event, name='caldav_get_event'),
    path('caldav/<str:calendar_id>/<str:event_uid>', views.get_event),
    path('.well-known/caldav/', views.well_known_caldav_redirect),
    path('.well-known/caldav', views.well_known_caldav_redirect, name='well_known_caldav'),

]
