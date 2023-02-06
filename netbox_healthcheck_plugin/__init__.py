"""Top-level package for NetBox HealthCheck Plugin."""

__author__ = """Arthur Hanson"""
__email__ = 'ahanson@netboxlabs.com'
__version__ = '0.1.0'


from extras.plugins import PluginConfig


class HealthCheckConfig(PluginConfig):
    name = 'netbox_healthcheck_plugin'
    verbose_name = 'NetBox HealthCheck Plugin'
    description = 'NetBox plugin for HealthCheck.'
    version = 'version'
    base_url = 'netbox_healthcheck_plugin'


config = HealthCheckConfig
