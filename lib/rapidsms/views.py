#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


from django.template import RequestContext
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.views.decorators.http import require_GET
from django.contrib.auth.views import login as django_login
from django.contrib.auth.views import logout as django_logout

from django.db import models
from .models import *

@require_GET
def dashboard(req):
    context = {} # the variables to be used in the template

    # list of models that may be summarized
    # with info that add_dashboard_widget needs to identify them
    context['models'] = [
        {
            'name': "%s (%s)" % (model.__name__, model._meta.app_label),
            'id': "%s+%s" % (model.__name__, model._meta.app_label)
        }
        for model in models.get_models()
        if not issubclass(model, WidgetBase)
           and not issubclass(model, WidgetEntryBase)
           and not model.__module__.startswith('django.contrib.')
    ]

    # 3 lists of currently saved widgets to be displayed in the 3 columns
    for i in 1,2,3:
        this_col = context["col%s" % i] = []
        for widget in Widget.objects.filter(column=i):
            this_col.append(widget.derivative)

    return render_to_response(
        'dashboard.html',
        context,
        context_instance=RequestContext(req))

def add_dashboard_widget(req):
    # if a nonempty string was submitted as the identifying info of a model,
    # create a widget to summarize the model's info
    if req.GET['model']:
        model_name, model_app_label = req.GET['model'].split('+')
        widg = Widget.create_and_link(title=req.GET['title'], column=req.GET['column'],
            model_name=model_name, model_app_label=model_app_label)
        ModelCount.create_and_link(widget=widg, label='Number Of %ss' % widg.model_name)

    # regardless, redirect to Dashboard
    """ ** TODO: **
    present some kind of error message if there's an error,
    present a "Widget Was Created!" message and highlight the newly
    created widget otherwise
    """
    return redirect('/')

def add_dashboard_widget_entry(req):
    # if all the info needed is there, create a new entry in the appropriate widget
    if req.GET['widget_id'] and req.GET['field'] and req.GET['stats']:
        widget = Widget.objects.get(pk=req.GET['widget_id'])
        FieldStats.create_and_link(widget=widget, label=req.GET['label'],
            field=req.GET['field'], statistic=req.GET['stats'])

    return redirect('/')

def delete_dashboard_widget(req):
    if req.GET.get('base_id', None):
        Widget.objects.get(pk=req.GET['base_id']).delete()
    return redirect('/')

""" ** TODO: **
def delete_dashboard_widget_entry(req):
    ...
"""

def login(req, template_name="rapidsms/login.html"):
    return django_login(req, **{"template_name" : template_name})


def logout(req, template_name="rapidsms/loggedout.html"):
    return django_logout(req, **{"template_name" : template_name})
