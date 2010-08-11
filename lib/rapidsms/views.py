#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


from django.template import RequestContext
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.views.decorators.http import require_GET
from django.contrib.auth.views import login as django_login
from django.contrib.auth.views import logout as django_logout

from django.db import models
from .widgets import *

@require_GET
def dashboard(req):
    context = {}
    context['models'] = [
        {
            'name': "%s (%s)" % (model.__name__, model._meta.app_label),
            'id': "%s+%s" % (model.__name__, model._meta.app_label)
        }
        for model in models.get_models()
        if not model.__name__ == 'WidgetBase'
           and not model.__name__.endswith('Widget')
           and not model.__module__.startswith('django.contrib.')
    ]
    for i in 1,2,3:
        this_col = context["col%s" % i] = []
        for widget in Widget.objects.filter(column=i):
            this_col.append(widget)

    return render_to_response(
        'dashboard.html',
        context,
        context_instance=RequestContext(req))

def add_dashboard_widget(req):
    if req.GET['model']:
        model_name, model_app_label = req.GET['model'].split('+')
        if req.GET['data'] == 'Count':
            CountWidget.objects.create(title=req.GET['title'], column=req.GET['column'],
                model_name=model_name, model_app_label=model_app_label)

    return redirect('/')

def delete_dashboard_widget(req):
    if req.GET.get('pk', None):
        Widget.objects.get(pk=req.GET['pk']).delete()
    return redirect('/')

def login(req, template_name="rapidsms/login.html"):
    return django_login(req, **{"template_name" : template_name})


def logout(req, template_name="rapidsms/loggedout.html"):
    return django_logout(req, **{"template_name" : template_name})
