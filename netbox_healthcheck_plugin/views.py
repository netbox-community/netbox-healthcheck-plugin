from django.views.generic import View
from health_check.views import MainView


class HealthCheckListView(MainView):
    template_name = 'netbox_healthcheck_plugin/healthcheck.html'
