from django.db.models import Count

from netbox.views import generic
from . import filtersets, forms, models, tables


class HealthCheckView(generic.ObjectView):
    queryset = models.HealthCheck.objects.all()


class HealthCheckListView(generic.ObjectListView):
    queryset = models.HealthCheck.objects.all()
    table = tables.HealthCheckTable


class HealthCheckEditView(generic.ObjectEditView):
    queryset = models.HealthCheck.objects.all()
    form = forms.HealthCheckForm


class HealthCheckDeleteView(generic.ObjectDeleteView):
    queryset = models.HealthCheck.objects.all()


