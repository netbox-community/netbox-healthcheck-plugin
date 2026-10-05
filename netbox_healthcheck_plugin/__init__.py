"""Top-level package for NetBox HealthCheck Plugin."""

__author__ = 'NetBox Labs'
__email__ = 'support@netboxlabs.com'
__version__ = '0.4.0'


from django.core.exceptions import ImproperlyConfigured

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
        'login_required': True,
        'checks': [
            'health_check.Database',
            'health_check.Cache',
            'netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck',
            'netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck',
        ],
    }

    @classmethod
    def validate(cls, user_config, netbox_version):
        super().validate(user_config, netbox_version)
        # Only a real bool: a string such as "false" is truthy, and None or 0 would quietly turn login off.
        if not isinstance(user_config['login_required'], bool):
            raise ImproperlyConfigured(
                f"PLUGINS_CONFIG['{cls.name}']['login_required'] must be True or False, "
                f'not {user_config["login_required"]!r}.'
            )


config = HealthCheckConfig
