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
        'netbox_healthcheck_plugin.backends',
    ]
    min_version = "v4.0-beta1"

config = HealthCheckConfig
