import functools
import inspect
import logging

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils.decorators import method_decorator
from health_check.views import HealthCheckView

from netbox.plugins import get_plugin_config
from utilities.views import TokenConditionalLoginRequiredMixin

# Check paths from django-health-check 3.x mapped to their 4.x equivalents, so existing
# PLUGINS_CONFIG['checks'] entries keep working after upgrading.
LEGACY_CHECKS = {
    'health_check.cache.backends.CacheBackend': 'health_check.Cache',
    'health_check.db.backends.DatabaseBackend': 'health_check.Database',
    'health_check.contrib.db_heartbeat.backends.DatabaseHeartBeatCheck': 'health_check.Database',
    'health_check.contrib.mail.backends.MailHealthCheck': 'health_check.Mail',
    'health_check.storage.backends.StorageHealthCheck': 'health_check.Storage',
    'health_check.storage.backends.DefaultFileStorageHealthCheck': 'health_check.Storage',
}

logger = logging.getLogger('netbox_healthcheck_plugin')


@functools.cache
def _warn_legacy_check(check):
    logger.warning("Health check '%s' is deprecated; use '%s' instead.", check, LEGACY_CHECKS[check])


def _resolve_legacy_check(check):
    if isinstance(check, str) and check in LEGACY_CHECKS:
        _warn_legacy_check(check)
        return LEGACY_CHECKS[check]
    return check


class HealthCheckListView(TokenConditionalLoginRequiredMixin, HealthCheckView):
    """Health check view that integrates django-health-check with NetBox UI.

    With the plugin's `login_required` setting enabled (the default), the view follows NetBox's own `LOGIN_REQUIRED`
    and accepts either a session or an API token, as NetBox's media view does.
    """

    template_name = 'netbox_healthcheck_plugin/healthcheck.html'

    # Overriding dispatch drops the decorator HealthCheckView applies to its own, so reapply it.
    @method_decorator(transaction.non_atomic_requests)
    async def dispatch(self, request, *args, **kwargs):
        if not get_plugin_config('netbox_healthcheck_plugin', 'login_required'):
            return await HealthCheckView.dispatch(self, request, *args, **kwargs)
        # NetBox's login mixin is sync and the session/token lookups hit the database, so run it off the event loop.
        # When access is allowed it returns HealthCheckView.dispatch's coroutine, which is awaited here.
        response = await sync_to_async(super().dispatch)(request, *args, **kwargs)
        if inspect.isawaitable(response):
            response = await response
        return response

    @property
    def checks(self):
        """Get health checks from plugin config or use defaults."""
        return [_resolve_legacy_check(check) for check in get_plugin_config('netbox_healthcheck_plugin', 'checks')]
