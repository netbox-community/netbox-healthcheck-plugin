"""Tests for netbox_healthcheck_plugin package."""

import dataclasses
from datetime import timedelta
from unittest.mock import MagicMock, patch

import redis
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from health_check import HealthCheck
from health_check.exceptions import ServiceUnavailable


class TestHealthCheckPlugin(TestCase):
    """Test suite for NetBox HealthCheck Plugin."""

    def test_plugin_config(self):
        """Test that plugin config is properly defined."""
        from netbox_healthcheck_plugin import HealthCheckConfig

        self.assertEqual(HealthCheckConfig.name, 'netbox_healthcheck_plugin')
        self.assertEqual(HealthCheckConfig.version, '0.4.0')
        self.assertEqual(HealthCheckConfig.min_version, '4.5.0')

    def test_plugin_default_settings(self):
        """Test that default settings are properly defined."""
        from netbox_healthcheck_plugin import HealthCheckConfig

        self.assertIn('checks', HealthCheckConfig.default_settings)
        default_checks = HealthCheckConfig.default_settings['checks']
        self.assertIsInstance(default_checks, list)
        self.assertGreater(len(default_checks), 0)
        # Verify default checks are present
        self.assertIn('health_check.Database', default_checks)
        self.assertIn('health_check.Cache', default_checks)
        self.assertIn('netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck', default_checks)
        self.assertIn('netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck', default_checks)

        self.assertIs(HealthCheckConfig.default_settings['login_required'], True)


@dataclasses.dataclass
class FailingCheck(HealthCheck):
    """A check that fails with a message naming an internal host, which anonymous responses must not reveal."""

    def run(self):
        raise ServiceUnavailable('redis.internal.example:6379 refused the connection')


FAILING_CHECK = f'{__name__}.FailingCheck'


class TestLoginRequiredValidation(TestCase):
    """Test that login_required must be a real bool."""

    def test_non_bool_rejected(self):
        """Values whose truthiness would mislead, such as the string "false" or None, are refused at startup."""
        from django.core.exceptions import ImproperlyConfigured

        from netbox_healthcheck_plugin import HealthCheckConfig

        for value in ('false', 'True', None, 0, 1, ''):
            with self.subTest(value=value), self.assertRaises(ImproperlyConfigured):
                HealthCheckConfig.validate({'login_required': value}, settings.RELEASE.version)

    def test_bool_and_default_accepted(self):
        """True, False and the default are accepted."""
        from netbox_healthcheck_plugin import HealthCheckConfig

        for user_config in ({'login_required': True}, {'login_required': False}, {}):
            with self.subTest(user_config=user_config):
                HealthCheckConfig.validate(user_config, settings.RELEASE.version)


class TestHealthCheckAccess(TestCase):
    """Test who gets the full report and who gets only the status."""

    url = reverse('plugins:netbox_healthcheck_plugin:healthcheck_list')
    BROWSER_ACCEPT = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'

    def setUp(self):
        from users.models import User

        self.user = User.objects.create_user(username='healthcheck')

    def plugin_config(self, **overrides):
        return override_settings(
            PLUGINS_CONFIG={
                **settings.PLUGINS_CONFIG,
                'netbox_healthcheck_plugin': {
                    **settings.PLUGINS_CONFIG['netbox_healthcheck_plugin'],
                    **overrides,
                },
            }
        )

    def create_token(self, **kwargs):
        from users.constants import TOKEN_PREFIX
        from users.models import Token

        token = Token.objects.create(user=self.user, **kwargs)
        return f'Bearer {TOKEN_PREFIX}{token.key}.{token.token}'

    def test_anonymous_browser_redirected_to_login(self):
        """By default an anonymous browser request is sent to the login page."""
        response = Client().get(self.url, HTTP_ACCEPT=self.BROWSER_ACCEPT)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])
        self.assertIn('Accept', response['Vary'])

    def test_anonymous_gets_status_only(self):
        """Anonymous non-browser requests get the overall status in the requested format, without check details."""
        cases = {
            'no Accept header': ({}, {}, 'text/plain; charset=utf-8', 'OK\n'),
            'wildcard Accept': ({}, {'HTTP_ACCEPT': '*/*'}, 'text/plain; charset=utf-8', 'OK\n'),
            'JSON preferred': (
                {},
                {'HTTP_ACCEPT': 'application/json, text/html;q=0.5'},
                'application/json',
                '{"status": "OK"}',
            ),
            'format overrides Accept': (
                {'format': 'json'},
                {'HTTP_ACCEPT': self.BROWSER_ACCEPT},
                'application/json',
                '{"status": "OK"}',
            ),
        }
        for name, (params, headers, content_type, body) in cases.items():
            with self.subTest(name):
                response = Client().get(self.url, params, **headers)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], content_type)
                self.assertEqual(response.content.decode(), body)
                self.assertIn('Accept', response['Vary'])
                self.assertIn('no-cache', response['Cache-Control'])

    def test_anonymous_failure_hides_details(self):
        """A failing check gives anonymous requests an unhealthy status without its error message."""
        with self.plugin_config(checks=['health_check.Database', FAILING_CHECK]):
            responses = {
                fmt: Client().get(self.url, {'format': fmt}) for fmt in ('text', 'json', 'openmetrics', 'atom', 'rss')
            }

        self.assertEqual(responses['text'].status_code, 500)
        self.assertEqual(responses['text'].content, b'Unhealthy\n')
        self.assertEqual(responses['json'].status_code, 500)
        self.assertEqual(responses['json'].json(), {'status': 'Unhealthy'})
        self.assertEqual(responses['openmetrics'].status_code, 200)
        self.assertIn(b'django_health_check_overall_status 0\n', responses['openmetrics'].content)
        self.assertNotIn(b'django_health_check_status{', responses['openmetrics'].content)
        for fmt in ('atom', 'rss'):
            self.assertEqual(responses[fmt].status_code, 200)
            self.assertIn(b'Unhealthy', responses[fmt].content)
        for fmt, response in responses.items():
            with self.subTest(fmt):
                self.assertNotIn(b'redis.internal', response.content)
                self.assertNotIn(b'FailingCheck', response.content)

    def test_anonymous_head_and_options(self):
        """HEAD and OPTIONS work anonymously; HEAD still reflects the checks' status."""
        with self.plugin_config(checks=[FAILING_CHECK]):
            head = Client().head(self.url)
        options = Client().options(self.url)

        self.assertEqual(head.status_code, 500)
        self.assertEqual(options.status_code, 200)
        self.assertIn('GET', options['Allow'])

    def test_post_not_allowed(self):
        """POST is rejected, with or without credentials, and doesn't run the checks."""
        with patch.object(FailingCheck, 'run') as run, self.plugin_config(checks=[FAILING_CHECK]):
            anonymous = Client().post(self.url)
            with_token = Client().post(self.url, HTTP_AUTHORIZATION=self.create_token())

        self.assertEqual(anonymous.status_code, 405)
        self.assertEqual(with_token.status_code, 405)
        run.assert_not_called()

    def test_session_user_gets_full_report(self):
        """A logged-in user sees each check's result."""
        client = Client()
        client.force_login(self.user)
        with self.plugin_config(checks=['health_check.Database', FAILING_CHECK]):
            response = client.get(self.url, {'format': 'json'})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(response.json()), 2)
        self.assertIn(b'redis.internal.example:6379', response.content)

    def test_session_user_gets_html_page(self):
        """A logged-in browser gets the NetBox-styled page."""
        client = Client()
        client.force_login(self.user)
        response = client.get(self.url, HTTP_ACCEPT=self.BROWSER_ACCEPT)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'netbox_healthcheck_plugin/healthcheck.html')

    def test_api_token_gets_full_report(self):
        """An API token gets the full report, so monitoring can authenticate without a session."""
        response = Client().get(self.url, {'format': 'openmetrics'}, HTTP_AUTHORIZATION=self.create_token())

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'django_health_check_status{check="Database"', response.content)

    def test_rejected_api_tokens_forbidden(self):
        """Invalid, expired, disabled and IP-restricted tokens get 403 with the reason, not a downgraded report."""
        cases = {
            'invalid': ('Bearer nbt_invalid.invalid', 'Invalid v2 token'),
            'expired': (self.create_token(expires=timezone.now() - timedelta(days=1)), 'Token expired'),
            'disabled': (self.create_token(enabled=False), 'Token disabled'),
            'IP not allowed': (self.create_token(allowed_ips=['192.0.2.0/24']), 'is not permitted'),
        }
        for name, (authorization, reason) in cases.items():
            with self.subTest(name):
                response = Client().get(self.url, HTTP_AUTHORIZATION=authorization)

                self.assertEqual(response.status_code, 403)
                self.assertIn(reason, response.content.decode())

    def test_database_error_during_authentication(self):
        """If the token can't be checked because the database is down, the request still gets the status."""
        from django.db import OperationalError

        with (
            patch('netbox_healthcheck_plugin.views.TokenAuthentication.authenticate', side_effect=OperationalError),
            self.assertLogs('netbox_healthcheck_plugin', level='WARNING'),
            self.plugin_config(checks=[FAILING_CHECK]),
        ):
            response = Client().get(self.url, {'format': 'openmetrics'}, HTTP_AUTHORIZATION=self.create_token())

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'django_health_check_overall_status 0\n', response.content)
        self.assertNotIn(b'redis.internal', response.content)

    def test_login_not_required_when_disabled(self):
        """With login_required off, anonymous requests get the full report."""
        with self.plugin_config(login_required=False):
            response = Client().get(self.url, {'format': 'json'})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('status', response.json())

    @override_settings(LOGIN_REQUIRED=False)
    def test_ignores_netbox_login_required(self):
        """login_required keeps the details private even when NetBox's own LOGIN_REQUIRED is off."""
        response = Client().get(self.url, {'format': 'json'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'OK'})


class TestHealthCheckConfiguration(TestCase):
    """Test health check configuration."""

    @patch('netbox_healthcheck_plugin.views.get_plugin_config')
    def test_default_checks_used(self, mock_get_config):
        """Test that default checks are used when configured."""
        from netbox_healthcheck_plugin.views import HealthCheckListView

        default_checks = [
            'health_check.Database',
            'health_check.Cache',
            'netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck',
            'netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck',
        ]
        mock_get_config.return_value = default_checks

        view = HealthCheckListView()
        checks = view.checks

        self.assertEqual(checks, default_checks)
        mock_get_config.assert_called_once_with('netbox_healthcheck_plugin', 'checks')

    @patch('netbox_healthcheck_plugin.views.get_plugin_config')
    def test_custom_checks_from_config(self, mock_get_config):
        """Test that custom checks from config are used."""
        from netbox_healthcheck_plugin.views import HealthCheckListView

        custom_checks = [
            'health_check.Database',
            'netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck',
        ]
        mock_get_config.return_value = custom_checks

        view = HealthCheckListView()
        checks = view.checks

        self.assertEqual(checks, custom_checks)
        self.assertEqual(len(checks), 2)
        mock_get_config.assert_called_once_with('netbox_healthcheck_plugin', 'checks')

    @patch('netbox_healthcheck_plugin.views.get_plugin_config')
    def test_empty_checks_list(self, mock_get_config):
        """Test behavior with empty checks list."""
        from netbox_healthcheck_plugin.views import HealthCheckListView

        mock_get_config.return_value = []

        view = HealthCheckListView()
        checks = view.checks

        self.assertEqual(checks, [])
        mock_get_config.assert_called_once_with('netbox_healthcheck_plugin', 'checks')

    @patch('netbox_healthcheck_plugin.views.get_plugin_config')
    def test_legacy_check_paths_resolved(self, mock_get_config):
        """Test that django-health-check 3.x check paths are mapped to their 4.x equivalents."""
        from netbox_healthcheck_plugin.views import HealthCheckListView, _warn_legacy_check

        mock_get_config.return_value = [
            'health_check.Database',
            'health_check.cache.backends.CacheBackend',
        ]
        _warn_legacy_check.cache_clear()

        view = HealthCheckListView()
        with self.assertLogs('netbox_healthcheck_plugin', level='WARNING'):
            checks = view.checks

        self.assertEqual(checks, ['health_check.Database', 'health_check.Cache'])

    @patch('netbox_healthcheck_plugin.views.get_plugin_config')
    def test_default_checks_instantiate(self, mock_get_config):
        """Test that every default check path imports and instantiates."""
        from health_check import HealthCheck

        from netbox_healthcheck_plugin import HealthCheckConfig
        from netbox_healthcheck_plugin.views import HealthCheckListView

        mock_get_config.return_value = HealthCheckConfig.default_settings['checks']

        checks = list(HealthCheckListView().get_checks())

        self.assertEqual(len(checks), len(HealthCheckConfig.default_settings['checks']))
        for check in checks:
            self.assertIsInstance(check, HealthCheck)

    @patch('netbox_healthcheck_plugin.views.get_plugin_config')
    def test_check_with_options(self, mock_get_config):
        """(path, options) entries pass keyword arguments to the check."""
        from health_check import Cache

        from netbox_healthcheck_plugin.views import HealthCheckListView

        mock_get_config.return_value = [('health_check.Cache', {'alias': 'default', 'key_prefix': 'netbox_probe'})]

        (check,) = HealthCheckListView().get_checks()

        self.assertIsInstance(check, Cache)
        self.assertEqual(check.key_prefix, 'netbox_probe')

    @patch('netbox_healthcheck_plugin.views.get_plugin_config')
    def test_legacy_check_path_with_options_resolved(self, mock_get_config):
        """Legacy 3.x paths are remapped inside (path, options) entries too, lists included."""
        from netbox_healthcheck_plugin.views import HealthCheckListView, _warn_legacy_check

        mock_get_config.return_value = [
            ('health_check.cache.backends.CacheBackend', {'alias': 'default'}),
            ['health_check.contrib.psutil.backends.DiskUsage', {'max_disk_usage_percent': 80}],
        ]
        _warn_legacy_check.cache_clear()

        with self.assertLogs('netbox_healthcheck_plugin', level='WARNING'):
            checks = HealthCheckListView().checks

        self.assertEqual(
            checks,
            [
                ('health_check.Cache', {'alias': 'default'}),
                ('health_check.contrib.psutil.Disk', {'max_disk_usage_percent': 80}),
            ],
        )


class TestCheckValidation(TestCase):
    """PLUGINS_CONFIG['checks'] is validated at startup, so a typo can't 500 every probe."""

    @patch('netbox_healthcheck_plugin.views.get_plugin_config')
    def test_valid_checks(self, mock_get_config):
        from netbox_healthcheck_plugin import HealthCheckConfig
        from netbox_healthcheck_plugin.views import _warn_legacy_check, validate_checks

        _warn_legacy_check.cache_clear()
        mock_get_config.return_value = [
            *HealthCheckConfig.default_settings['checks'],
            ('health_check.Cache', {'alias': 'default'}),
            ['health_check.cache.backends.CacheBackend', {}],
        ]
        with self.assertLogs('netbox_healthcheck_plugin', level='WARNING'):
            validate_checks()

    @patch('netbox_healthcheck_plugin.views.get_plugin_config')
    def test_invalid_checks(self, mock_get_config):
        import dataclasses

        from django.core.exceptions import ImproperlyConfigured
        from health_check import HealthCheck

        from netbox_healthcheck_plugin.views import validate_checks

        # Like the psutil checks' hostname, but without needing psutil installed.
        @dataclasses.dataclass
        class InitFalseCheck(HealthCheck):
            hostname: str = dataclasses.field(default='x', init=False)

            def run(self):
                pass

        cases = [
            ('health_check.Nope', 'cannot be imported'),
            (('health_check.Cache', {'aliass': 'default'}), 'has invalid options'),
            (('health_check.Cache', ['alias']), 'options must be a dict'),
            (('health_check.Cache', {}, {}), 'must be a dotted path or a (path, options) pair'),
            ('django.conf.settings', 'is not a django-health-check HealthCheck'),
            ((InitFalseCheck, {'hostname': 'x'}), 'has invalid options'),
        ]
        for entry, message in cases:
            with self.subTest(entry=entry):
                mock_get_config.return_value = [entry]
                with self.assertRaisesMessage(ImproperlyConfigured, message):
                    validate_checks()

    @override_settings(HEALTH_CHECK={'DISK_USAGE_MAX': 80, 'MEMORY_MIN': 200})
    def test_legacy_health_check_setting_warns(self):
        from netbox_healthcheck_plugin.views import warn_legacy_settings

        with self.assertLogs('netbox_healthcheck_plugin', level='WARNING') as logs:
            warn_legacy_settings()
        self.assertIn('max_disk_usage_percent', logs.output[0])

    def test_no_health_check_setting_is_quiet(self):
        from netbox_healthcheck_plugin.views import warn_legacy_settings

        with self.assertNoLogs('netbox_healthcheck_plugin', level='WARNING'):
            warn_legacy_settings()


def _mock_connection(**connection_kwargs):
    """Return a mock Redis client whose pool carries the given connection kwargs."""
    connection = MagicMock()
    connection.connection_pool = MagicMock(spec=['connection_kwargs'])
    connection.connection_pool.connection_kwargs = {
        'host': 'redis.example.com',
        'port': 6379,
        'db': 0,
    } | connection_kwargs
    return connection


class TestNetBoxRedisCacheHealthCheck(TestCase):
    """Tests for the NetBox Redis cache health check backend."""

    def test_uses_django_redis_default_cache(self):
        """The check targets the client behind CACHES['default'] (REDIS['caching'] in testing/configuration.py)."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        self.assertEqual(
            NetBoxRedisCacheHealthCheck().labels,
            {
                'check': 'NetBoxRedisCacheHealthCheck',
                'redis_instance': 'caching',
                'host': 'localhost',
                'port': '6379',
                'db': '1',
            },
        )

    def test_repr(self):
        """repr is redis:caching, and is the JSON key, so it must stay stable."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        self.assertEqual(repr(NetBoxRedisCacheHealthCheck()), 'redis:caching')

    @override_settings(
        CACHES={
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': 'redis://mymaster/1',
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.SentinelClient',
                    'SENTINELS': [('sentinel.example.com', 26379)],
                    'PASSWORD': 'hunter2',
                },
            }
        },
        DJANGO_REDIS_CONNECTION_FACTORY='django_redis.pool.SentinelConnectionFactory',
    )
    def test_sentinel(self):
        """A Sentinel-backed cache (REDIS['caching']['SENTINELS']) is labelled by service, not localhost."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        labels = NetBoxRedisCacheHealthCheck().labels
        self.assertEqual(labels['service'], 'mymaster')
        self.assertEqual(labels['db'], '1')
        self.assertNotIn('host', labels)
        self.assertNotIn('hunter2', str(labels))

    def test_run_success_keeps_shared_pool_open(self):
        """run() PINGs and leaves django-redis's shared connection pool open."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        connection = _mock_connection()
        with patch('django_redis.get_redis_connection', return_value=connection) as mock_get:
            self.assertIsNone(NetBoxRedisCacheHealthCheck().run())

        mock_get.assert_called_once_with('default')
        connection.ping.assert_called_once()
        connection.close.assert_not_called()

    def test_run_connection_error(self):
        """redis.ConnectionError maps to ServiceUnavailable naming the target."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        connection = _mock_connection()
        connection.ping.side_effect = redis.ConnectionError('Connection refused')
        with (
            patch('django_redis.get_redis_connection', return_value=connection),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            NetBoxRedisCacheHealthCheck().run()

        self.assertIn('redis.example.com:6379/0', str(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)

    def test_run_redis_error_not_connection_error(self):
        """Non-connection redis errors (e.g. DataError) still map to ServiceUnavailable."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        connection = _mock_connection()
        connection.ping.side_effect = redis.DataError('bad command')
        with (
            patch('django_redis.get_redis_connection', return_value=connection),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            NetBoxRedisCacheHealthCheck().run()

        self.assertIn('DataError', str(ctx.exception))

    def test_run_generic_exception_keeps_context(self):
        """Non-redis errors from PING still fail the check with its target."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        connection = _mock_connection()
        connection.ping.side_effect = OSError('bad certificate')
        with (
            patch('django_redis.get_redis_connection', return_value=connection),
            self.assertLogs('netbox_healthcheck_plugin', level='WARNING'),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            NetBoxRedisCacheHealthCheck().run()

        self.assertEqual(str(ctx.exception), 'Unavailable: Redis OSError for redis.example.com:6379/0')

    def test_run_error_text_not_shown(self):
        """The exception text is never shown, since it may echo credentials (even as a substring of the host)."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        connection = _mock_connection(host='redis', password='redis')
        connection.ping.side_effect = redis.ConnectionError('Error connecting to redis://:redis@redis:6379/0')
        with (
            patch('django_redis.get_redis_connection', return_value=connection),
            self.assertLogs('netbox_healthcheck_plugin', level='WARNING'),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            NetBoxRedisCacheHealthCheck().run()

        self.assertEqual(str(ctx.exception), 'Unavailable: Redis ConnectionError for redis:6379/0')

    def test_run_client_configuration_error(self):
        """A client that cannot be built fails the check without leaking the exception text."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        backend = NetBoxRedisCacheHealthCheck()
        with (
            patch('django_redis.get_redis_connection', side_effect=NotImplementedError('secret detail')),
            self.assertLogs('netbox_healthcheck_plugin', level='WARNING'),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            backend.run()

        self.assertIn('caching', str(ctx.exception))
        self.assertIn('NotImplementedError', str(ctx.exception))
        self.assertNotIn('secret detail', str(ctx.exception))

    def test_labels_without_client(self):
        """Labels fall back to settings.REDIS when the client cannot be built, so the series doesn't change."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        healthy = NetBoxRedisCacheHealthCheck().labels
        with patch('django_redis.get_redis_connection', side_effect=NotImplementedError):
            labels = NetBoxRedisCacheHealthCheck().labels

        self.assertEqual(labels, healthy)

    @override_settings(REDIS={'caching': {'URL': 'unix:///run/redis/redis.sock?db=3', 'PASSWORD': 'hunter2'}})
    def test_labels_without_client_url(self):
        """The settings fallback parses REDIS[...]['URL'] and never labels credentials."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        with patch('django_redis.get_redis_connection', side_effect=NotImplementedError):
            labels = NetBoxRedisCacheHealthCheck().labels

        self.assertEqual(
            labels,
            {
                'check': 'NetBoxRedisCacheHealthCheck',
                'redis_instance': 'caching',
                'path': '/run/redis/redis.sock',
                'db': '3',
            },
        )

    @override_settings(REDIS={'caching': {'HOST': 'redis.example.com'}})
    def test_labels_without_client_defaults(self):
        """The settings fallback applies NetBox's PORT and DATABASE defaults, matching the healthy labels."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        with patch('django_redis.get_redis_connection', side_effect=NotImplementedError):
            labels = NetBoxRedisCacheHealthCheck().labels

        self.assertEqual(
            labels,
            {
                'check': 'NetBoxRedisCacheHealthCheck',
                'redis_instance': 'caching',
                'host': 'redis.example.com',
                'port': '6379',
                'db': '0',
            },
        )

    @override_settings(REDIS={'caching': {'SENTINELS': [('sentinel', 26379)], 'PASSWORD': 'hunter2'}})
    def test_labels_without_client_sentinel_defaults(self):
        """Without SENTINEL_SERVICE the fallback uses NetBox's 'default' service, not HOST/PORT."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        with patch('django_redis.get_redis_connection', side_effect=NotImplementedError):
            labels = NetBoxRedisCacheHealthCheck().labels

        self.assertEqual(
            labels,
            {'check': 'NetBoxRedisCacheHealthCheck', 'redis_instance': 'caching', 'service': 'default', 'db': '0'},
        )

    @override_settings(REDIS={})
    def test_labels_without_client_or_settings(self):
        """With neither a client nor a REDIS entry, only check and redis_instance are labelled."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        with patch('django_redis.get_redis_connection', side_effect=NotImplementedError):
            labels = NetBoxRedisCacheHealthCheck().labels

        self.assertEqual(labels, {'check': 'NetBoxRedisCacheHealthCheck', 'redis_instance': 'caching'})

    def test_run_against_local_redis(self):
        """End to end against the Redis in testing/configuration.py."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        self.assertIsNone(NetBoxRedisCacheHealthCheck().run())


class TestNetBoxRedisTasksHealthCheck(TestCase):
    """Tests for the NetBox Redis tasks health check backend."""

    def test_uses_rq_default_queue(self):
        """The check targets RQ_QUEUES['default'] (REDIS['tasks'] in testing/configuration.py)."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        self.assertEqual(
            NetBoxRedisTasksHealthCheck().labels,
            {
                'check': 'NetBoxRedisTasksHealthCheck',
                'redis_instance': 'tasks',
                'host': 'localhost',
                'port': '6379',
                'db': '0',
            },
        )

    def test_repr(self):
        """repr is redis:tasks."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        self.assertEqual(repr(NetBoxRedisTasksHealthCheck()), 'redis:tasks')

    @override_settings(
        RQ_QUEUES={
            'default': {
                'SENTINELS': [('sentinel.example.com', 26379)],
                'MASTER_NAME': 'tasks-master',
                'DB': 2,
                'PASSWORD': 'hunter2',
                'CONNECTION_KWARGS': {'socket_connect_timeout': 10},
            }
        }
    )
    def test_sentinel(self):
        """REDIS['tasks']['SENTINELS'] is honoured instead of pinging localhost."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        backend = NetBoxRedisTasksHealthCheck()
        labels = backend.labels
        self.assertEqual(labels['service'], 'tasks-master')
        self.assertEqual(labels['db'], '2')
        self.assertNotIn('host', labels)
        self.assertNotIn('hunter2', str(labels))
        self.assertEqual(backend._target(), "sentinel service 'tasks-master'")

    @override_settings(RQ_QUEUES={'default': {'URL': 'unix:///run/redis/redis.sock', 'DB': 3}})
    def test_unix_socket_url(self):
        """REDIS['tasks']['URL'] (e.g. a Unix socket) is honoured."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        backend = NetBoxRedisTasksHealthCheck()
        self.assertEqual(backend.labels['path'], '/run/redis/redis.sock')
        self.assertEqual(backend.labels['db'], '3')
        self.assertEqual(backend._target(), 'unix:///run/redis/redis.sock')

    @override_settings(RQ_QUEUES={})
    def test_missing_default_queue(self):
        """A missing RQ queue fails the check rather than silently pinging localhost."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        with (
            self.assertLogs('netbox_healthcheck_plugin', level='WARNING'),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            NetBoxRedisTasksHealthCheck().run()
        self.assertIn('tasks', str(ctx.exception))

    def test_run_closes_connection(self):
        """run() PINGs and closes the client django-rq built for it."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        connection = _mock_connection()
        with patch('django_rq.queues.get_redis_connection', return_value=connection):
            self.assertIsNone(NetBoxRedisTasksHealthCheck().run())

        connection.ping.assert_called_once()
        connection.close.assert_called_once()

    def test_run_closes_connection_on_error(self):
        """The client is closed even when PING fails."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        connection = _mock_connection()
        connection.ping.side_effect = redis.ConnectionError('refused')
        with (
            patch('django_rq.queues.get_redis_connection', return_value=connection),
            self.assertLogs('netbox_healthcheck_plugin', level='WARNING'),
            self.assertRaises(ServiceUnavailable),
        ):
            NetBoxRedisTasksHealthCheck().run()

        connection.close.assert_called_once()

    def test_close_error_does_not_mask_result(self):
        """An error from close() is logged, and doesn't replace the PING result."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        connection = _mock_connection()
        connection.close.side_effect = redis.ConnectionError('already closed')
        with patch('django_rq.queues.get_redis_connection', return_value=connection):
            with self.assertLogs('netbox_healthcheck_plugin', level='WARNING'):
                self.assertIsNone(NetBoxRedisTasksHealthCheck().run())

            connection.ping.side_effect = redis.TimeoutError('timed out')
            with (
                self.assertLogs('netbox_healthcheck_plugin', level='WARNING'),
                self.assertRaises(ServiceUnavailable) as ctx,
            ):
                NetBoxRedisTasksHealthCheck().run()
        self.assertIn('TimeoutError', str(ctx.exception))

    def test_run_against_local_redis(self):
        """End to end against the Redis in testing/configuration.py."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        self.assertIsNone(NetBoxRedisTasksHealthCheck().run())


class TestOpenMetrics(TestCase):
    """The OpenMetrics output tells the two Redis instances apart."""

    @patch('netbox_healthcheck_plugin.views.get_plugin_config')
    def test_redis_labels(self, mock_get_config):
        from django.contrib.auth import get_user_model

        mock_get_config.return_value = [
            'netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck',
            'netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck',
        ]
        client = Client()
        client.force_login(get_user_model().objects.create_user(username='probe'))
        response = client.get(reverse('plugins:netbox_healthcheck_plugin:healthcheck_list'), {'format': 'openmetrics'})

        body = response.content.decode()
        self.assertIn(
            'django_health_check_status{check="NetBoxRedisCacheHealthCheck",redis_instance="caching",'
            'host="localhost",port="6379",db="1"} 1',
            body,
        )
        self.assertIn('redis_instance="tasks"', body)
