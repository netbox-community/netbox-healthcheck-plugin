"""Top-level package for NetBox HealthCheck Plugin."""

__author__ = """Arthur Hanson"""
__email__ = 'ahanson@netboxlabs.com'
__version__ = '0.1.2'


from extras.plugins import PluginConfig


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
        'health_check.contrib.redis',
    ]


config = HealthCheckConfig
