import functools
import logging

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


class HealthCheckListView(HealthCheckView):
    """Health check view that integrates django-health-check with NetBox UI."""

    template_name = 'netbox_healthcheck_plugin/healthcheck.html'

    @property
    def checks(self):
        """Get health checks from plugin config or use defaults."""
        return [_resolve_legacy_check(check) for check in get_plugin_config('netbox_healthcheck_plugin', 'checks')]
