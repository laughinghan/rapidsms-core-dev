#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from django.conf.urls.defaults import *
from . import views

urlpatterns = patterns('',
    url(r'^$', views.dashboard),
    url(r'^dashboard/add/widget/$', views.add_dashboard_widget),
    url(r'^dashboard/add/widget_entry/$', views.add_dashboard_widget_entry),
    url(r'^dashboard/del/$', views.delete_dashboard_widget),
    url(r'^accounts/login/$', views.login),
    url(r'^accounts/logout/$', views.logout),
)
