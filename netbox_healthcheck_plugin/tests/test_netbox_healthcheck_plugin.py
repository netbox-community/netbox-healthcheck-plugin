"""Tests for netbox_healthcheck_plugin package."""

import sys
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse


class TestHealthCheckPlugin(TestCase):
    """Test suite for NetBox HealthCheck Plugin."""

    def test_plugin_config(self):
        """Test that plugin config is properly defined."""
        from netbox_healthcheck_plugin import HealthCheckConfig

        self.assertEqual(HealthCheckConfig.name, 'netbox_healthcheck_plugin')
        self.assertEqual(HealthCheckConfig.version, '0.3.0')
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

    def test_healthcheck_endpoint_exists(self):
        """Test that the healthcheck URL is accessible."""
        client = Client()
        url = reverse('plugins:netbox_healthcheck_plugin:healthcheck_list')
        response = client.get(url)

        # Should return 200 or redirect (depending on NetBox setup)
        self.assertIn(response.status_code, [200, 302])


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
