"""Django app configuration for custom health check backends."""

from django.apps import AppConfig
from health_check.plugins import plugin_dir


class NetBoxRedisHealthCheckConfig(AppConfig):
    """App config that registers the NetBox Redis health check backends."""

    name = 'netbox_healthcheck_plugin.backends'
    label = 'netbox_healthcheck_backends'
    verbose_name = 'NetBox Health Check Backends'

    def ready(self):
        from .redis import NetBoxRedisCacheHealthCheck, NetBoxRedisTasksHealthCheck
        # Register health checks for both Redis instances used by NetBox
        plugin_dir.register(NetBoxRedisCacheHealthCheck)
        plugin_dir.register(NetBoxRedisTasksHealthCheck)
