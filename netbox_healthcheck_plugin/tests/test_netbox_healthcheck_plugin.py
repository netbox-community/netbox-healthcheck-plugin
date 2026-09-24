"""Tests for netbox_healthcheck_plugin package."""

from unittest.mock import MagicMock, patch

import redis
from django.test import Client, TestCase, override_settings
from django.urls import reverse


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
                'instance': 'caching',
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

    def test_run_generic_exception_not_caught(self):
        """Non-redis errors propagate to django-health-check's handler."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        connection = _mock_connection()
        connection.ping.side_effect = TypeError('bad argument')
        with patch('django_redis.get_redis_connection', return_value=connection), self.assertRaises(TypeError):
            NetBoxRedisCacheHealthCheck().run()

    def test_run_password_scrubbed_from_error(self):
        """If the underlying exception echoes the password back, it gets scrubbed."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        connection = _mock_connection(password='hunter2')
        connection.ping.side_effect = redis.ConnectionError('Error connecting to redis://:hunter2@h:6379/0')
        with (
            patch('django_redis.get_redis_connection', return_value=connection),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            NetBoxRedisCacheHealthCheck().run()

        self.assertNotIn('hunter2', str(ctx.exception))
        self.assertIn('REDACTED', str(ctx.exception))

    def test_run_client_configuration_error(self):
        """A client that cannot be built fails the check without leaking the exception text."""
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        backend = NetBoxRedisCacheHealthCheck()
        with (
            patch('django_redis.get_redis_connection', side_effect=NotImplementedError('secret detail')),
            self.assertLogs('netbox_healthcheck_plugin', level='ERROR'),
            self.assertRaises(ServiceUnavailable) as ctx,
        ):
            backend.run()

        self.assertIn('caching', str(ctx.exception))
        self.assertIn('NotImplementedError', str(ctx.exception))
        self.assertNotIn('secret detail', str(ctx.exception))

    def test_labels_without_client(self):
        """Labels fall back to check and instance when the client cannot be built."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        with patch('django_redis.get_redis_connection', side_effect=NotImplementedError):
            labels = NetBoxRedisCacheHealthCheck().labels

        self.assertEqual(labels, {'check': 'NetBoxRedisCacheHealthCheck', 'instance': 'caching'})

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
                'instance': 'tasks',
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

        with self.assertLogs('netbox_healthcheck_plugin', level='ERROR'), self.assertRaises(ServiceUnavailable) as ctx:
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
            self.assertRaises(ServiceUnavailable),
        ):
            NetBoxRedisTasksHealthCheck().run()

        connection.close.assert_called_once()

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
            'django_health_check_status{check="NetBoxRedisCacheHealthCheck",instance="caching",'
            'host="localhost",port="6379",db="1"} 1',
            body,
        )
        self.assertIn('instance="tasks"', body)
