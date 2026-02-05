from health_check.views import HealthCheckView


class HealthCheckListView(HealthCheckView):
    template_name = 'netbox_healthcheck_plugin/healthcheck.html'
    checks = [
        'health_check.Database',
        'netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck',
        'netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck',
    ]
