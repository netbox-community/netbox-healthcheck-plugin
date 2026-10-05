import functools
import inspect
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from health_check import HealthCheck
from health_check.views import HealthCheckView

from netbox.plugins import get_plugin_config

# Check paths from django-health-check 3.x mapped to their 4.x equivalents, so existing
# PLUGINS_CONFIG['checks'] entries keep working after upgrading.
LEGACY_CHECKS = {
    'health_check.cache.backends.CacheBackend': 'health_check.Cache',
    'health_check.db.backends.DatabaseBackend': 'health_check.Database',
    'health_check.contrib.db_heartbeat.backends.DatabaseHeartBeatCheck': 'health_check.Database',
    'health_check.contrib.mail.backends.MailHealthCheck': 'health_check.Mail',
    'health_check.storage.backends.StorageHealthCheck': 'health_check.Storage',
    'health_check.storage.backends.DefaultFileStorageHealthCheck': 'health_check.Storage',
    'health_check.contrib.psutil.backends.DiskUsage': 'health_check.contrib.psutil.Disk',
    'health_check.contrib.psutil.backends.MemoryUsage': 'health_check.contrib.psutil.Memory',
}

logger = logging.getLogger('netbox_healthcheck_plugin')


@functools.cache
def _warn_legacy_check(check):
    logger.warning("Health check '%s' is deprecated; use '%s' instead.", check, LEGACY_CHECKS[check])


def _resolve_legacy_check(check):
    # A check may be given as a (path, options) pair to pass keyword arguments to it.
    if isinstance(check, (list, tuple)) and len(check) == 2:
        return (_resolve_legacy_check(check[0]), check[1])
    if isinstance(check, str) and check in LEGACY_CHECKS:
        _warn_legacy_check(check)
        return LEGACY_CHECKS[check]
    return check


def _check_entry_error(entry):
    """Return why a resolved `checks` entry can't be instantiated, or None if it can."""
    if isinstance(entry, (list, tuple)):
        if len(entry) != 2:
            return 'must be a dotted path or a (path, options) pair'
        check, options = entry
        if not isinstance(options, dict):
            return f'options must be a dict, not {type(options).__name__}'
    else:
        check, options = entry, {}
    if isinstance(check, str):
        try:
            check = import_string(check)
        except ImportError as e:
            return f'cannot be imported ({e})'
    if not (isinstance(check, type) and issubclass(check, HealthCheck)):
        return 'is not a django-health-check HealthCheck'
    try:
        inspect.signature(check).bind(**options)
    except TypeError as e:
        return f'has invalid options ({e})'
    return None


def validate_checks():
    """
    Validate PLUGINS_CONFIG['netbox_healthcheck_plugin']['checks'] at startup.

    A bad entry would otherwise fail every request with a 500 and run no checks at all,
    which a probe reads as NetBox being down.
    """
    errors = [
        f'{entry!r} {error}'
        for entry in get_plugin_config('netbox_healthcheck_plugin', 'checks')
        if (error := _check_entry_error(_resolve_legacy_check(entry)))
    ]
    if errors:
        raise ImproperlyConfigured(
            "Invalid PLUGINS_CONFIG['netbox_healthcheck_plugin']['checks']: " + '; '.join(errors)
        )


def warn_legacy_settings():
    """Warn when django-health-check 3.x's HEALTH_CHECK setting is set; 4.x ignores it."""
    if getattr(settings, 'HEALTH_CHECK', None):
        logger.warning(
            'The HEALTH_CHECK setting is no longer read, so checks use their default thresholds. Set them as '
            "options in PLUGINS_CONFIG['netbox_healthcheck_plugin']['checks'] instead: DISK_USAGE_MAX becomes "
            "('health_check.contrib.psutil.Disk', {'max_disk_usage_percent': ...}), and MEMORY_MIN (MB free) "
            "becomes ('health_check.contrib.psutil.Memory', {'min_gibibytes_available': ...}) in GiB; Memory "
            'also fails at 90% used unless max_memory_usage_percent is changed.'
        )


class HealthCheckListView(HealthCheckView):
    """Health check view that integrates django-health-check with NetBox UI."""

    template_name = 'netbox_healthcheck_plugin/healthcheck.html'

    @property
    def checks(self):
        """Get health checks from plugin config or use defaults."""
        return [_resolve_legacy_check(check) for check in get_plugin_config('netbox_healthcheck_plugin', 'checks')]
