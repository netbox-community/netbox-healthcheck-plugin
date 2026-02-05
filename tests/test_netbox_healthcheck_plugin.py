#!/usr/bin/env python

"""Tests for `netbox_healthcheck_plugin` package."""

import pytest
from unittest.mock import MagicMock, patch


class TestBuildRedisUrl:
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
        assert url == 'redis://redis.example.com:6379/0'

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
        assert url == 'redis://:secret@redis.example.com:6379/1'

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
        assert url == 'redis://redisuser:secret@redis.example.com:6379/2'

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
        assert url == 'rediss://redis.example.com:6380/0'

    def test_defaults(self):
        """Test that defaults are applied for missing config."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_from_config

        config = {}
        url = build_redis_url_from_config(config)
        assert url == 'redis://localhost:6379/0'


class TestBuildRedisUrlOptions:
    """Tests for Redis URL options building."""

    def test_no_ssl(self):
        """Test that no options are returned without SSL."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_options

        config = {'SSL': False}
        options = build_redis_url_options(config)
        assert options == {}

    def test_ssl_insecure(self):
        """Test SSL with insecure skip verify."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_options
        import ssl

        config = {
            'SSL': True,
            'INSECURE_SKIP_TLS_VERIFY': True,
        }
        options = build_redis_url_options(config)
        assert options.get('ssl_cert_reqs') == ssl.CERT_NONE

    def test_ssl_with_ca_cert(self):
        """Test SSL with CA certificate path."""
        from netbox_healthcheck_plugin.backends.redis import build_redis_url_options

        config = {
            'SSL': True,
            'CA_CERT_PATH': '/etc/ssl/certs/ca-bundle.crt',
        }
        options = build_redis_url_options(config)
        assert options.get('ssl_ca_certs') == '/etc/ssl/certs/ca-bundle.crt'


class TestNetBoxRedisCacheHealthCheck:
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
        assert backend._redis_url == 'redis://cache-redis-host:6379/1'

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_repr(self, mock_settings):
        """Test that repr is redis:caching."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck

        mock_settings.REDIS = {'caching': {'HOST': 'localhost'}}

        backend = NetBoxRedisCacheHealthCheck()
        assert repr(backend) == 'redis:caching'

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
        assert len(backend.errors) == 0

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_check_status_connection_error(self, mock_settings):
        """Test health check with connection error."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisCacheHealthCheck
        from health_check.exceptions import ServiceUnavailable
        import redis

        mock_settings.REDIS = {'caching': {'HOST': 'nonexistent-host'}}

        backend = NetBoxRedisCacheHealthCheck()

        with patch.object(redis.Redis, 'from_url') as mock_from_url:
            mock_from_url.side_effect = redis.ConnectionError("Connection refused")
            with pytest.raises(ServiceUnavailable):
                backend.check_status()


class TestNetBoxRedisTasksHealthCheck:
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
        assert backend._redis_url == 'redis://tasks-redis-host:6380/2'

    @patch('netbox_healthcheck_plugin.backends.redis.settings')
    def test_repr(self, mock_settings):
        """Test that repr is redis:tasks."""
        from netbox_healthcheck_plugin.backends.redis import NetBoxRedisTasksHealthCheck

        mock_settings.REDIS = {'tasks': {'HOST': 'localhost'}}

        backend = NetBoxRedisTasksHealthCheck()
        assert repr(backend) == 'redis:tasks'

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
        assert len(backend.errors) == 0


