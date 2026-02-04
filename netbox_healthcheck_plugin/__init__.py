"""Top-level package for NetBox HealthCheck Plugin."""

__author__ = """Arthur Hanson"""
__email__ = 'ahanson@netboxlabs.com'
__version__ = '0.3.0'


from netbox.plugins import PluginConfig


class HealthCheckConfig(PluginConfig):
    name = 'netbox_healthcheck_plugin'
    verbose_name = 'NetBox HealthCheck Plugin'
    description = 'NetBox plugin for HealthCheck.'
    version = 'version'
    base_url = 'netbox_healthcheck_plugin'
    django_apps = [
        'health_check',
        'health_check.db',
        'health_check.contrib.migrations',
        # Use our custom Redis backend that reads from NetBox's REDIS config
        # instead of health_check.contrib.redis which expects REDIS_URL
        'netbox_healthcheck_plugin.backends',
    ]
    min_version = "v4.0-beta1"

config = HealthCheckConfig
