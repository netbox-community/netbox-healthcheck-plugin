"""Tests for netbox_healthcheck_plugin package."""

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

    def test_healthcheck_endpoint_exists(self):
        """Test that the healthcheck URL is accessible."""
        client = Client()
        url = reverse('plugins:netbox_healthcheck_plugin:healthcheck_list')
        response = client.get(url)

        # Should return 200 or redirect (depending on NetBox setup)
        self.assertIn(response.status_code, [200, 302])


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
        """Test that defaults are applied for missing config."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        config = {}
        url = build_redis_url_from_config(config)
        self.assertEqual(url, 'redis://localhost:6379/0')


class TestBuildRedisUrlOptions(TestCase):
    """Tests for Redis URL options building."""

    def test_no_ssl(self):
        """Test that no options are returned without SSL."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_options

        config = {'SSL': False}
        options = build_redis_url_options(config)
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

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_repr(self, mock_settings):
        """Test that repr is redis:caching."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'localhost'}}

        backend = NetBoxRedisCacheHealthCheck()
        self.assertEqual(repr(backend), 'redis:caching')

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    @patch('netbox_healthcheck_plugin.backends.redis.redis')
    def test_check_status_success(self, mock_redis_module, mock_settings):
        """Test successful health check."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'localhost'}}
        mock_connection = MagicMock()
        mock_redis_module.Redis.from_url.return_value = mock_connection

        backend = NetBoxRedisCacheHealthCheck()
        backend.check_status()

        mock_redis_module.Redis.from_url.assert_called_once()
        mock_connection.ping.assert_called_once()
        self.assertEqual(len(backend.errors), 0)

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_check_status_connection_error(self, mock_settings):
        """Test health check with connection error."""
        import redis
        from health_check.exceptions import ServiceUnavailable

        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'nonexistent-host'}}

        backend = NetBoxRedisCacheHealthCheck()

        with patch.object(redis.Redis, 'from_url') as mock_from_url:
            mock_from_url.side_effect = redis.ConnectionError('Connection refused')
            with self.assertRaises(ServiceUnavailable):
                backend.check_status()


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
    @patch('netbox_healthcheck_plugin.backends.redis.redis')
    def test_check_status_success(self, mock_redis_module, mock_settings):
        """Test successful health check."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        mock_settings.REDIS = {'tasks': {'HOST': 'localhost'}}
        mock_connection = MagicMock()
        mock_redis_module.Redis.from_url.return_value = mock_connection

        backend = NetBoxRedisTasksHealthCheck()
        backend.check_status()

        mock_redis_module.Redis.from_url.assert_called_once()
        mock_connection.ping.assert_called_once()
        self.assertEqual(len(backend.errors), 0)
