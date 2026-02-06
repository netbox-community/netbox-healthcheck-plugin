from health_check.views import MainView


class HealthCheckListView(MainView):
    """Health check view that integrates django-health-check with NetBox UI."""

    template_name = 'netbox_healthcheck_plugin/healthcheck.html'
