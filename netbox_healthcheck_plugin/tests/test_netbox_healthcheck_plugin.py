"""Tests for netbox_healthcheck_plugin package."""

import dataclasses
import sys
from datetime import timedelta
from unittest.mock import MagicMock, patch

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


class TestBuildRedisUrl(TestCase):
    """Tests for Redis URL building from NetBox config."""

    def test_basic_config(self):
        """Test basic Redis config without auth."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        config = {
            'HOST': 'redis.example.com',
            'PORT': 6379,
            'DATABASE': 0,
        }
        url = build_redis_url_from_config(config)
        self.assertEqual(url, 'redis://redis.example.com:6379/0')

    def test_with_password(self):
        """Test Redis config with password only."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        config = {
            'HOST': 'redis.example.com',
            'PORT': 6379,
            'DATABASE': 1,
            'PASSWORD': 'secret',
        }
        url = build_redis_url_from_config(config)
        self.assertEqual(url, 'redis://:secret@redis.example.com:6379/1')

    def test_with_username_and_password(self):
        """Test Redis config with username and password."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        config = {
            'HOST': 'redis.example.com',
            'PORT': 6379,
            'DATABASE': 2,
            'USERNAME': 'redisuser',
            'PASSWORD': 'secret',
        }
        url = build_redis_url_from_config(config)
        self.assertEqual(url, 'redis://redisuser:secret@redis.example.com:6379/2')

    def test_with_username_only(self):
        """Test Redis config with username but no password."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        config = {
            'HOST': 'redis.example.com',
            'PORT': 6379,
            'DATABASE': 0,
            'USERNAME': 'redisuser',
        }
        url = build_redis_url_from_config(config)
        self.assertEqual(url, 'redis://redisuser@redis.example.com:6379/0')

    def test_with_ssl(self):
        """Test Redis config with SSL enabled."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        config = {
            'HOST': 'redis.example.com',
            'PORT': 6380,
            'DATABASE': 0,
            'SSL': True,
        }
        url = build_redis_url_from_config(config)
        self.assertEqual(url, 'rediss://redis.example.com:6380/0')

    def test_defaults(self):
        """build_redis_url_from_config applies redis-py defaults for missing keys."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        config = {}
        url = build_redis_url_from_config(config)
        self.assertEqual(url, 'redis://localhost:6379/0')

    def test_none_credentials(self):
        """USERNAME/PASSWORD set to None are treated as unset."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        config = {'HOST': 'redis.example.com', 'USERNAME': None, 'PASSWORD': None}
        url = build_redis_url_from_config(config)
        self.assertEqual(url, 'redis://redis.example.com:6379/0')

    def test_password_with_special_chars_is_urlencoded(self):
        """Passwords with reserved URL characters must be percent-encoded."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        config = {
            'HOST': 'redis.example.com',
            'PORT': 6379,
            'DATABASE': 0,
            'PASSWORD': 'p@ss:w/rd!',
        }
        url = build_redis_url_from_config(config)
        # @ -> %40, : -> %3A, / -> %2F, ! -> %21
        self.assertEqual(url, 'redis://:p%40ss%3Aw%2Frd%21@redis.example.com:6379/0')

    def test_password_with_slash_is_urlencoded(self):
        """Slash in password is encoded (quote defaults miss '/', we use safe='')."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        url = build_redis_url_from_config({'HOST': 'h', 'PORT': 6379, 'DATABASE': 0, 'PASSWORD': 'a/b'})
        self.assertEqual(url, 'redis://:a%2Fb@h:6379/0')

    def test_username_with_special_chars_is_urlencoded(self):
        """Usernames with reserved URL characters must be percent-encoded."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        config = {
            'HOST': 'redis.example.com',
            'PORT': 6379,
            'DATABASE': 0,
            'USERNAME': 'user@acl',
            'PASSWORD': 'secret',
        }
        url = build_redis_url_from_config(config)
        self.assertEqual(url, 'redis://user%40acl:secret@redis.example.com:6379/0')


class TestBuildRedisUrlOptions(TestCase):
    """Tests for Redis URL options building."""

    def test_no_ssl(self):
        """Test that no options are returned without SSL."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_options

        config = {'SSL': False}
        options = build_redis_url_options(config)
        self.assertEqual(options, {})

    def test_ssl_enabled_without_extras(self):
        """SSL True with no INSECURE_SKIP_TLS_VERIFY or CA_CERT_PATH yields empty options."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_options

        options = build_redis_url_options({'SSL': True})
        self.assertEqual(options, {})

    def test_ssl_insecure(self):
        """Test SSL with insecure skip verify."""
        import ssl

        from netbox_healthcheck_plugin.backends.redis import build_redis_url_options

        config = {
            'SSL': True,
            'INSECURE_SKIP_TLS_VERIFY': True,
        }
        options = build_redis_url_options(config)
        self.assertEqual(options.get('ssl_cert_reqs'), ssl.CERT_NONE)

    def test_ssl_with_ca_cert(self):
        """Test SSL with CA certificate path."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_options

        config = {
            'SSL': True,
            'CA_CERT_PATH': '/etc/ssl/certs/ca-bundle.crt',
        }
        options = build_redis_url_options(config)
        self.assertEqual(options.get('ssl_ca_certs'), '/etc/ssl/certs/ca-bundle.crt')


class TestNetBoxRedisCacheHealthCheck(TestCase):
    """Tests for the NetBox Redis cache health check backend."""

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_reads_from_caching_config(self, mock_settings):
        """Test that the backend reads from NetBox's REDIS caching config."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {
            'caching': {
                'HOST': 'cache-redis-host',
                'PORT': 6379,
                'DATABASE': 1,
            },
            'tasks': {
                'HOST': 'tasks-redis-host',
                'PORT': 6380,
                'DATABASE': 2,
            },
        }

        backend = NetBoxRedisCacheHealthCheck()
        self.assertEqual(backend._redis_url, 'redis://cache-redis-host:6379/1')
        self.assertIsNone(backend._config_error)

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_repr(self, mock_settings):
        """Test that repr is redis:caching."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'localhost'}}

        backend = NetBoxRedisCacheHealthCheck()
        self.assertEqual(repr(backend), 'redis:caching')

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_run_success(self, mock_settings):
        """run() returns None and closes the connection on success."""
        import redis

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'localhost'}}
        mock_connection = MagicMock()

        backend = NetBoxRedisCacheHealthCheck()
        with patch.object(redis.Redis, 'from_url', return_value=mock_connection) as mock_from_url:
            self.assertIsNone(backend.run())

        mock_from_url.assert_called_once()
        mock_connection.ping.assert_called_once()
        mock_connection.close.assert_called_once()

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_run_connection_error(self, mock_settings):
        """redis.ConnectionError maps to ServiceUnavailable."""
        import redis
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'nonexistent-host'}}

        backend = NetBoxRedisCacheHealthCheck()
        mock_connection = MagicMock()
        mock_connection.ping.side_effect = redis.ConnectionError('Connection refused')
        with (
            patch.object(redis.Redis, 'from_url', return_value=mock_connection),
            self.assertRaises(ServiceUnavailable),
        ):
            backend.run()
        mock_connection.close.assert_called_once()

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_run_redis_error_not_connection_error(self, mock_settings):
        """Non-connection redis errors (e.g. DataError) still map to ServiceUnavailable."""
        import redis
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'localhost'}}
        backend = NetBoxRedisCacheHealthCheck()
        mock_connection = MagicMock()
        # DataError is a RedisError but NOT a ConnectionError subclass,
        # so it hits the second except branch.
        mock_connection.ping.side_effect = redis.DataError('bad command')
        with (
            patch.object(redis.Redis, 'from_url', return_value=mock_connection),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            backend.run()

        self.assertIn('DataError', str(ctx.exception))
        mock_connection.close.assert_called_once()

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_run_generic_exception_not_caught(self, mock_settings):
        """Non-redis errors (e.g. TypeError from bad config) propagate to the framework."""
        import redis

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'localhost'}}
        backend = NetBoxRedisCacheHealthCheck()
        mock_connection = MagicMock()
        mock_connection.ping.side_effect = TypeError('bad argument')
        with (
            patch.object(redis.Redis, 'from_url', return_value=mock_connection),
            self.assertRaises(TypeError),
        ):
            backend.run()
        mock_connection.close.assert_called_once()

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_run_password_masked_in_error(self, mock_settings):
        """Error messages include the masked URL, not the raw password."""
        import redis
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'h', 'PORT': 6379, 'DATABASE': 0, 'PASSWORD': 'topsecret'}}
        backend = NetBoxRedisCacheHealthCheck()
        mock_connection = MagicMock()
        mock_connection.ping.side_effect = redis.ConnectionError('refused')
        with (
            patch.object(redis.Redis, 'from_url', return_value=mock_connection),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            backend.run()

        msg = str(ctx.exception)
        self.assertNotIn('topsecret', msg)
        self.assertIn(':REDACTED@', msg)

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_run_real_url_scrubbed_from_inner_message(self, mock_settings):
        """If the underlying exception echoes the real URL back, it gets scrubbed."""
        import redis
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'h', 'PORT': 6379, 'DATABASE': 0, 'PASSWORD': 'hunter2'}}
        backend = NetBoxRedisCacheHealthCheck()
        mock_connection = MagicMock()
        mock_connection.ping.side_effect = redis.ConnectionError(f'Error connecting to {backend._redis_url}: refused')
        with (
            patch.object(redis.Redis, 'from_url', return_value=mock_connection),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            backend.run()

        self.assertNotIn('hunter2', str(ctx.exception))

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_run_no_mask_when_no_auth(self, mock_settings):
        """URLs without credentials don't get rewritten by the masking logic."""
        import redis
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'plain', 'PORT': 6379, 'DATABASE': 0}}
        backend = NetBoxRedisCacheHealthCheck()
        mock_connection = MagicMock()
        mock_connection.ping.side_effect = redis.ConnectionError('refused')
        with (
            patch.object(redis.Redis, 'from_url', return_value=mock_connection),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            backend.run()

        self.assertIn('redis://plain:6379/0', str(ctx.exception))

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_run_no_mask_when_username_only(self, mock_settings):
        """Username-only URLs have no colon before @, so the masker leaves them alone."""
        import redis
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'h', 'PORT': 6379, 'DATABASE': 0, 'USERNAME': 'ro'}}
        backend = NetBoxRedisCacheHealthCheck()
        mock_connection = MagicMock()
        mock_connection.ping.side_effect = redis.ConnectionError('refused')
        with (
            patch.object(redis.Redis, 'from_url', return_value=mock_connection),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            backend.run()

        self.assertIn('ro@h:6379/0', str(ctx.exception))

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_run_raises_for_missing_config(self, mock_settings):
        """run() fails loudly when the key is absent from settings.REDIS."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'tasks': {'HOST': 'localhost'}}  # no 'caching' key
        backend = NetBoxRedisCacheHealthCheck()
        self.assertIsNotNone(backend._config_error)

        with self.assertRaises(ServiceUnavailable) as ctx:
            backend.run()
        self.assertIn('caching', str(ctx.exception))

    def test_run_raises_when_redis_setting_absent(self):
        """Entirely missing settings.REDIS is still a hard fail, not a silent default."""
        from django.conf import settings
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        with patch.object(settings, 'REDIS', {}, create=True):
            backend = NetBoxRedisCacheHealthCheck()
            self.assertIsNotNone(backend._config_error)
            with self.assertRaises(ServiceUnavailable):
                backend.run()

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_run_redis_library_not_installed(self, mock_settings):
        """Missing redis-py dependency surfaces as ServiceUnavailable."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'localhost'}}
        backend = NetBoxRedisCacheHealthCheck()

        with patch.dict(sys.modules, {'redis': None}), self.assertRaises(ServiceUnavailable) as ctx:
            backend.run()
        self.assertIn('redis library not installed', str(ctx.exception))


class TestNetBoxRedisTasksHealthCheck(TestCase):
    """Tests for the NetBox Redis tasks health check backend."""

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_reads_from_tasks_config(self, mock_settings):
        """Test that the backend reads from NetBox's REDIS tasks config."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        mock_settings.REDIS = {
            'caching': {
                'HOST': 'cache-redis-host',
                'PORT': 6379,
                'DATABASE': 1,
            },
            'tasks': {
                'HOST': 'tasks-redis-host',
                'PORT': 6380,
                'DATABASE': 2,
            },
        }

        backend = NetBoxRedisTasksHealthCheck()
        self.assertEqual(backend._redis_url, 'redis://tasks-redis-host:6380/2')

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_repr(self, mock_settings):
        """Test that repr is redis:tasks."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        mock_settings.REDIS = {'tasks': {'HOST': 'localhost'}}

        backend = NetBoxRedisTasksHealthCheck()
        self.assertEqual(repr(backend), 'redis:tasks')

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_run_success(self, mock_settings):
        """run() returns None and closes the connection on success."""
        import redis

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        mock_settings.REDIS = {'tasks': {'HOST': 'localhost'}}
        mock_connection = MagicMock()

        backend = NetBoxRedisTasksHealthCheck()
        with patch.object(redis.Redis, 'from_url', return_value=mock_connection) as mock_from_url:
            self.assertIsNone(backend.run())

        mock_from_url.assert_called_once()
        mock_connection.ping.assert_called_once()
        mock_connection.close.assert_called_once()
