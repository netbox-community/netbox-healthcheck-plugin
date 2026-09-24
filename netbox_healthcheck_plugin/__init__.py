"""Top-level package for NetBox HealthCheck Plugin."""

__author__ = 'NetBox Labs'
__email__ = 'support@netboxlabs.com'
__version__ = '0.4.0'


from netbox.plugins import PluginConfig


class HealthCheckConfig(PluginConfig):
    """NetBox HealthCheck Plugin configuration."""

    name = 'netbox_healthcheck_plugin'
    label = 'netbox_healthcheck_plugin'
    verbose_name = 'NetBox HealthCheck Plugin'
    description = 'NetBox plugin for HealthCheck.'
    version = __version__
    author = __author__
    author_email = __email__
    # Not the scaffold's 'healthcheck-plugin': monitoring probes already target
    # /plugins/netbox_healthcheck_plugin/healthcheck/.
    base_url = 'netbox_healthcheck_plugin'
    min_version = '4.5.0'
    max_version = '4.7.99'
    django_apps = [
        'health_check',
        'netbox_healthcheck_plugin.backends',
    ]
    default_settings = {
        'checks': [
            'health_check.Database',
            'health_check.Cache',
            'netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck',
            'netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck',
        ]
    }


config = HealthCheckConfig
