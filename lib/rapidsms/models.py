#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


from datetime import datetime
from django.db import models
from .utils.modules import try_import, get_classes
from .conf import settings


class ExtensibleModelBase(models.base.ModelBase):
    def __new__(cls, name, bases, attrs):
        module_name = attrs["__module__"]
        app_label = module_name.split('.')[-2]
        extensions = _find_extensions(app_label, name)
        bases = tuple(extensions) + bases

        return super(ExtensibleModelBase, cls).__new__(
            cls, name, bases, attrs)


def _find_extensions(app_label, model_name):
    ext = []

    suffix = "extensions.%s.%s" % (
        app_label, model_name.lower())

    modules = filter(None, [
        try_import("%s.%s" % (app_name, suffix))
        for app_name in settings.INSTALLED_APPS ])

    for module in modules:
        for cls in get_classes(module, models.Model):
            ext.append(cls)

    return ext


class Backend(models.Model):
    """
    This model isn't really a backend. Those are regular Python classes,
    in rapidsms/backends. This is just a stub model to provide a primary
    key for each running backend, so other models can be linked to it
    with ForeignKeys.
    """

    name = models.CharField(max_length=20, unique=True)

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s>' %\
            (type(self).__name__, self)


class App(models.Model):
    """
    This model isn't really a RapidSMS App. Like Backend, it's just a
    stub model to provide a primary key for each app, so other models
    can be linked to it.

    The Django ContentType stuff doesn't quite work here, since not all
    RapidSMS apps are valid Django apps. It would be nice to fill in the
    gaps and inherit from it at some point in the future.

    Instances of this model are generated by the update_apps management
    command, (which is hooked on Router startup (TODO: webui startup)),
    and probably shouldn't be messed with after that.
    """

    module = models.CharField(max_length=100, unique=True)
    active = models.BooleanField()

    def __unicode__(self):
        return self.module

    def __repr__(self):
        return '<%s: %s>' %\
            (type(self).__name__, self)


class ContactBase(models.Model):
    name  = models.CharField(max_length=100, blank=True)

    # the spec: http://www.w3.org/International/articles/language-tags/Overview
    # reference:http://www.iana.org/assignments/language-subtag-registry
    language = models.CharField(max_length=6, blank=True, help_text=
        "The language which this contact prefers to communicate in, as "
        "a W3C language tag. If this field is left blank, RapidSMS will "
        "default to: " + settings.LANGUAGE_CODE)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name or "Anonymous"

    def __repr__(self):
        return '<%s: %s>' %\
            (type(self).__name__, self)

    @property
    def is_anonymous(self):
        return not self.name

    @property
    def default_connection(self):
        """
        Return the default connection for this person.
        """
        # TODO: this is defined totally arbitrarily for a future 
        # sane implementation
        if self.connection_set.count() > 0:
            return self.connection_set.all()[0]
        return None

class Contact(ContactBase):
    __metaclass__ = ExtensibleModelBase


class ConnectionBase(models.Model):
    """
    This model pairs a Backend object with an identity unique to it (eg.
    a phone number, email address, or IRC nick), so RapidSMS developers
    need not worry about which backend a messge originated from.
    """

    backend  = models.ForeignKey(Backend)
    identity = models.CharField(max_length=100)
    contact  = models.ForeignKey(Contact, null=True, blank=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return "%s via %s" %\
            (self.identity, self.backend)

    def __repr__(self):
        return '<%s: %s>' %\
            (type(self).__name__, self)


class Connection(ConnectionBase):
    __metaclass__ = ExtensibleModelBase


class PolymorphicModel(models.Model):
    """
    An abstract Model base class that provides descendant Model classes
    with more polymorphism than normal Django Models.

    Note: Overrides primary key to be base_id.

    Usage:
        class BaseClass(PolymorphicModel):
            bar = models.CharField(max_length=100)
            def foo(self):
                return bar
        class DerivedClass(models.Model):
            def foo(self):
                return "derived " + bar
    later...
        DerivedClass.create_and_link(bar='bar')
        assertEquals('derived bar',
            BaseClass.objects.get(bar='bar').derivative.foo())
    """
    base_id = models.AutoField(primary_key=True)
        # because id is overwritten in derived classes

    derivative_name = models.CharField(max_length=50)
    derivative_app_label = models.CharField(max_length=100)

    @classmethod
    def create_and_link(cls, **kwargs):
        "Create a Widget and link to the derivative class"
        return cls.objects.create(derivative_name=cls.__name__,
            derivative_app_label=cls._meta.app_label, **kwargs)

    @property
    def derivative(self):
        return models.get_model(self.derivative_app_label, self.derivative_name)\
            .objects.get(base_id=self.base_id)

    class Meta:
        abstract = True


class WidgetBase(PolymorphicModel):
    """
    A Dashboard widget that displays at-a-glance summary statistics info.
    """
    title = models.CharField(max_length=40)
    column = models.PositiveSmallIntegerField()

    model_name = models.CharField(max_length=100)
    model_app_label = models.CharField(max_length=100)

    @property
    def model(self):
        return models.get_model(self.model_app_label, self.model_name)

    def field_names(self):
        return [field.name for field in self.model._meta.fields if
            not isinstance(field, models.AutoField)]

    def __unicode__(self):
        return self.title or (str(self.model_name).split('.')[-1] + " Dashboard Widget")

    def __repr__(self):
        return '<%s: %s>' %\
            (type(self).__name__, self)


class Widget(WidgetBase):
    __metaclass__ = ExtensibleModelBase


class WidgetEntryBase(PolymorphicModel):
    """
    A line of data in a Dashboard Widget.
    """
    widget = models.ForeignKey(Widget, related_name='data')
    label = models.CharField(max_length=50)


class WidgetEntry(WidgetEntryBase):
    __metaclass__ = ExtensibleModelBase


class ModelCount(WidgetEntry):
    """
    Counts how many objects of the widget's model are in the database.
    """
    def data(self):
        return self.widget.model.objects.count()
    class Meta:
        proxy = True


class FieldStats(WidgetEntry):
    """
    Applies one of Django's statistical aggregation functions to a field
    of the widget's model.
    """
    field = models.CharField(max_length=50)
    statistic = models.CharField(max_length=10)

    def data(self):
        return self.widget.model.objects.aggregate(
            data=models.__dict__[self.statistic](self.field))['data']

