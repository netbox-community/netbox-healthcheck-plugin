"""Django app configuration for custom health check backends."""

from django.apps import AppConfig


class NetBoxRedisHealthCheckConfig(AppConfig):
    """App config for the NetBox Redis health check backends."""

    name = 'netbox_healthcheck_plugin.backends'
    label = 'netbox_healthcheck_backends'
    verbose_name = 'NetBox Health Check Backends'
