from health_check.views import HealthCheckView


class HealthCheckListView(HealthCheckView):
    """Health check view that integrates django-health-check with NetBox UI."""

    template_name = 'netbox_healthcheck_plugin/healthcheck.html'
    checks = [
        'health_check.Database',
        'health_check.cache.backends.CacheBackend',
        'netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck',
        'netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck',
    ]
