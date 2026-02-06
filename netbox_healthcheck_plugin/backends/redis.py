"""
Redis health check backend for NetBox.

This backend reads Redis connection settings from NetBox's REDIS configuration
dict instead of expecting a REDIS_URL setting. NetBox uses separate HOST, PORT,
DATABASE, PASSWORD, etc. fields rather than a connection URL.
"""

from django.conf import settings
from health_check.backends import HealthCheck
from health_check.exceptions import ServiceUnavailable


def build_redis_url_from_config(redis_config: dict) -> str:
    """
    Build a Redis URL from NetBox's REDIS configuration dict.

    Args:
        redis_config: Dict with HOST, PORT, DATABASE, PASSWORD, USERNAME, SSL keys

    Returns:
        Redis URL string (e.g., "redis://host:6379/0" or "rediss://user:pass@host:6379/0")

    Note:
        If HOST, PORT, or DATABASE are not specified, defaults to localhost:6379/0.
        This is intentional to match django-redis's default behavior.
    """
    host = redis_config.get('HOST', 'localhost')
    port = redis_config.get('PORT', 6379)
    database = redis_config.get('DATABASE', 0)
    password = redis_config.get('PASSWORD', '')
    username = redis_config.get('USERNAME', '')
    use_ssl = redis_config.get('SSL', False)

    scheme = 'rediss' if use_ssl else 'redis'

    auth = ''
    if password:
        auth = f'{username}:{password}@' if username else f':{password}@'
    elif username:
        auth = f'{username}@'

    return f'{scheme}://{auth}{host}:{port}/{database}'


def build_redis_url_options(redis_config: dict) -> dict:
    """
    Build Redis connection options for SSL/TLS from NetBox's REDIS configuration.

    Args:
        redis_config: Dict with SSL, INSECURE_SKIP_TLS_VERIFY, CA_CERT_PATH keys

    Returns:
        Dict of redis-py connection options for SSL/TLS
    """
    options = {}
    use_ssl = redis_config.get('SSL', False)

    if use_ssl:
        import ssl

        if redis_config.get('INSECURE_SKIP_TLS_VERIFY', False):
            options['ssl_cert_reqs'] = ssl.CERT_NONE
        ca_cert = redis_config.get('CA_CERT_PATH', '')
        if ca_cert:
            options['ssl_ca_certs'] = ca_cert

    return options


class BaseNetBoxRedisHealthCheck(HealthCheck):
    """
    Base health check backend for Redis that reads from NetBox's REDIS configuration.

    NetBox stores Redis configuration in settings.REDIS as a dict with 'caching'
    and 'tasks' keys, each containing HOST, PORT, DATABASE, PASSWORD, etc.

    Subclasses should set `redis_config_key` to specify which Redis instance to check.
    """

    redis_config_key: str = 'caching'

    def __init__(self):
        super().__init__()
        # Build connection parameters from NetBox's REDIS config at instantiation time
        redis_settings = getattr(settings, 'REDIS', {})
        redis_config = redis_settings.get(self.redis_config_key, {})

        # Warn if using default configuration (empty config dict)
        if not redis_config:
            import warnings

            warnings.warn(
                f"No Redis configuration found for '{self.redis_config_key}' in settings.REDIS. "
                f'Using defaults: localhost:6379/0. This may indicate a configuration issue.',
                RuntimeWarning,
                stacklevel=2,
            )

        self._redis_url = build_redis_url_from_config(redis_config)
        self._redis_url_options = build_redis_url_options(redis_config)

    def check_status(self):
        """Check Redis connectivity by issuing a PING command."""
        try:
            import redis
        except ImportError as e:
            raise ServiceUnavailable('redis library not installed') from e

        # Mask password in URL for error messages
        display_url = self._redis_url
        if '@' in display_url and ':' in display_url.split('@')[0]:
            # Replace password with asterisks
            parts = display_url.split('@')
            auth_parts = parts[0].rsplit(':', 1)
            if len(auth_parts) == 2:
                display_url = f'{auth_parts[0]}:***@{parts[1]}'

        try:
            connection = redis.Redis.from_url(self._redis_url, **self._redis_url_options)
            connection.ping()
        except redis.ConnectionError as e:
            raise ServiceUnavailable(f'Redis connection error to {display_url}: {e}') from e
        except Exception as e:
            raise ServiceUnavailable(f'Redis error connecting to {display_url}: {e}') from e

    def __repr__(self):
        """Return a unique identifier for this health check."""
        return f'redis:{self.redis_config_key}'


class NetBoxRedisCacheHealthCheck(BaseNetBoxRedisHealthCheck):
    """Health check for NetBox's caching Redis instance."""

    redis_config_key = 'caching'


class NetBoxRedisTasksHealthCheck(BaseNetBoxRedisHealthCheck):
    """Health check for NetBox's tasks/RQ Redis instance."""

    redis_config_key = 'tasks'


# Backwards compatibility alias
NetBoxRedisHealthCheck = NetBoxRedisCacheHealthCheck
