"""Top-level package for NetBox HealthCheck Plugin."""

__author__ = 'NetBox Labs'
__email__ = 'support@netboxlabs.com'
__version__ = '0.3.0'


from netbox.plugins import PluginConfig


class HealthCheckConfig(PluginConfig):
    name = 'netbox_healthcheck_plugin'
    verbose_name = 'NetBox HealthCheck Plugin'
    description = 'NetBox plugin for HealthCheck.'
    version = '0.3.0'
    author = 'NetBox Labs'
    author_email = 'support@netboxlabs.com'
    base_url = 'netbox_healthcheck_plugin'
    django_apps = [
        'health_check',
        'health_check.cache',
        'netbox_healthcheck_plugin.backends',
    ]
    min_version = '4.5.0'
    max_version = '4.5.x'
    default_settings = {
        'checks': [
            'health_check.Database',
            'health_check.cache.backends.CacheBackend',
            'netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck',
            'netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck',
        ]
    }


config = HealthCheckConfig
