import datetime
import functools
import logging

from asgiref.sync import sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.views import redirect_to_login
from django.db import DatabaseError, transaction
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils.cache import add_never_cache_headers, patch_vary_headers
from django.utils.decorators import method_decorator
from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed
from health_check.views import HealthCheckView, MediaType
from rest_framework.exceptions import AuthenticationFailed

from netbox.api.authentication import TokenAuthentication
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
}

# ?format= values HealthCheckView answers with something other than HTML.
NON_HTML_FORMATS = {'json', 'text', 'atom', 'rss', 'openmetrics'}

logger = logging.getLogger('netbox_healthcheck_plugin')


@functools.cache
def _warn_legacy_check(check):
    logger.warning("Health check '%s' is deprecated; use '%s' instead.", check, LEGACY_CHECKS[check])


def _wants_html(request):
    """Return True if the client explicitly prefers HTML, as browsers do.

    Wildcards (`*/*`, `text/*`) and a missing Accept header don't count: curl and probes such as Kubernetes send `*/*`.
    """
    if request.GET.get('format') in NON_HTML_FORMATS:
        return False
    try:
        media_types = list(MediaType.parse_header(request.headers.get('accept', '')))
    except ValueError:
        return False
    return bool(media_types) and media_types[0].mime_type in ('text/html', 'application/xhtml+xml')


def _resolve_legacy_check(check):
    if isinstance(check, str) and check in LEGACY_CHECKS:
        _warn_legacy_check(check)
        return LEGACY_CHECKS[check]
    return check


class HealthCheckListView(HealthCheckView):
    """Health check view that integrates django-health-check with NetBox UI.

    With the plugin's `login_required` setting enabled (the default), only a logged-in session or a NetBox API token
    gets the full report. Anonymous browsers are sent to the login page, and any other anonymous request still runs the
    checks but gets only the overall status, so probes need no credentials and learn nothing about the backends.
    """

    template_name = 'netbox_healthcheck_plugin/healthcheck.html'

    # Whether the response lists each check and its error, or only the overall status.
    detailed = True

    # Overriding dispatch drops the decorator HealthCheckView applies to its own, so reapply it.
    @method_decorator(transaction.non_atomic_requests)
    async def dispatch(self, request, *args, **kwargs):
        if get_plugin_config('netbox_healthcheck_plugin', 'login_required'):
            # The session and token lookups hit the database, so run them off the event loop.
            denied = await sync_to_async(self.authenticate)(request)
            if denied is not None:
                patch_vary_headers(denied, ['Accept'])
                add_never_cache_headers(denied)
                return denied
            self.detailed = request.user.is_authenticated
        return await super().dispatch(request, *args, **kwargs)

    def authenticate(self, request):
        """Authenticate the request by session or API token, returning a response if it must be turned away."""
        try:
            if not request.user.is_authenticated and (auth_info := TokenAuthentication().authenticate(request)):
                request.user, request.auth = auth_info
        except AuthenticationFailed as e:
            return HttpResponseForbidden(f'Invalid token: {e.detail}', content_type='text/plain; charset=utf-8')
        except DatabaseError:
            # Without the database the credentials can't be checked, but the checks themselves still can: answer as
            # for an anonymous request, so the outage shows up as a failing status rather than a server error.
            logger.warning('Could not authenticate the health check request; reporting status only.', exc_info=True)
            request.user = AnonymousUser()
        if not request.user.is_authenticated and _wants_html(request):
            return redirect_to_login(request.get_full_path())
        return None

    def render_to_response(self, context, **response_kwargs):
        if not self.detailed:
            return self.render_to_response_text(response_kwargs.get('status', 200))
        return super().render_to_response(context, **response_kwargs)

    def render_to_response_json(self, status):
        if not self.detailed:
            return JsonResponse({'status': self.overall_status}, status=status)
        return super().render_to_response_json(status)

    def render_to_response_text(self, status):
        if not self.detailed:
            return HttpResponse(f'{self.overall_status}\n', content_type='text/plain; charset=utf-8', status=status)
        return super().render_to_response_text(status)

    def render_to_response_openmetrics(self):
        if not self.detailed:
            healthy = self.overall_status == 'OK'
            lines = [
                (
                    '# HELP django_health_check_overall_status Overall health check status '
                    '(1 = all healthy, 0 = at least one unhealthy)'
                ),
                '# TYPE django_health_check_overall_status gauge',
                f'django_health_check_overall_status {healthy:d}',
                '# EOF',
            ]
            return HttpResponse(
                '\n'.join(lines) + '\n',
                content_type='application/openmetrics-text; version=1.0.0; charset=utf-8',
                status=200,  # Prometheus expects 200 even if checks fail, as upstream's full report does
            )
        return super().render_to_response_openmetrics()

    def render_to_response_atom(self):
        return super().render_to_response_atom() if self.detailed else self._render_status_feed(Atom1Feed)

    def render_to_response_rss(self):
        return super().render_to_response_rss() if self.detailed else self._render_status_feed(Rss201rev2Feed)

    @property
    def overall_status(self):
        return 'Unhealthy' if any(result.error for result in self.results) else 'OK'

    def _render_status_feed(self, feed_class):
        """Render a feed with a single item for the overall status."""
        link = self.request.build_absolute_uri(self.request.path)
        errors = [result.error for result in self.results if result.error]
        # As upstream does, an unhealthy item is dated by its (earliest) error and a healthy one by the epoch.
        published_at = (
            min(e.timestamp for e in errors) if errors else datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
        )
        feed = feed_class(
            title='Health Check Status',
            link=link,
            description='Current status of system health checks',
            feed_url=self.request.build_absolute_uri(),
        )
        feed.add_item(
            title='NetBox',
            link=link,
            description=self.overall_status,
            pubdate=published_at,
            updateddate=published_at,
            author_name=self.feed_author,
            categories=['error', 'unhealthy'] if errors else ['healthy'],
        )
        return HttpResponse(feed.writeString('utf-8'), content_type=feed.content_type, status=200)

    @property
    def checks(self):
        """Get health checks from plugin config or use defaults."""
        return [_resolve_legacy_check(check) for check in get_plugin_config('netbox_healthcheck_plugin', 'checks')]
