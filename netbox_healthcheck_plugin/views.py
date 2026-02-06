from health_check.views import HealthCheckView
from netbox.plugins import get_plugin_config


class HealthCheckListView(HealthCheckView):
    """Health check view that integrates django-health-check with NetBox UI."""

    template_name = 'netbox_healthcheck_plugin/healthcheck.html'

    @property
    def checks(self):
        """Get health checks from plugin config or use defaults."""
        return get_plugin_config('netbox_healthcheck_plugin', 'checks')
