"""
Redis health check backend for NetBox.

This backend reads Redis connection settings from NetBox's REDIS configuration
dict instead of expecting a REDIS_URL setting. NetBox uses separate HOST, PORT,
DATABASE, PASSWORD, etc. fields rather than a connection URL.
"""

import dataclasses
from urllib.parse import quote

from django.conf import settings
from health_check.base import HealthCheck
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
    password = quote(redis_config.get('PASSWORD', ''), safe='')
    username = quote(redis_config.get('USERNAME', ''), safe='')
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


@dataclasses.dataclass(repr=False)
class BaseNetBoxRedisHealthCheck(HealthCheck):
    """
    Base health check backend for Redis that reads from NetBox's REDIS configuration.

    NetBox stores Redis configuration in settings.REDIS as a dict with 'caching'
    and 'tasks' keys, each containing HOST, PORT, DATABASE, PASSWORD, etc.

    Subclasses should set `redis_config_key` to specify which Redis instance to check.
    """

    redis_config_key: str = 'caching'

    def __post_init__(self):
        """Read and validate the NetBox Redis config at instantiation time.

        If the expected key is missing from settings.REDIS we record the error
        here and surface it from run(); we deliberately do NOT fall back to
        localhost defaults, because that would let a misconfigured deployment
        silently report healthy by pinging a different Redis (or nothing at all).
        """
        redis_settings = getattr(settings, 'REDIS', {})
        redis_config = redis_settings.get(self.redis_config_key, {})

        if not redis_config:
            self._config_error: str | None = (
                f"No Redis configuration found for '{self.redis_config_key}' in settings.REDIS"
            )
            self._redis_url = ''
            self._redis_url_options: dict = {}
            return

        self._config_error = None
        self._redis_url = build_redis_url_from_config(redis_config)
        self._redis_url_options = build_redis_url_options(redis_config)

    def run(self):
        """Check Redis connectivity by issuing a PING command."""
        if self._config_error:
            raise ServiceUnavailable(self._config_error)

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

        def _safe_msg(exc: Exception) -> str:
            """Strip the real URL (which contains the password) from the error message."""
            return str(exc).replace(self._redis_url, display_url)

        try:
            connection = redis.Redis.from_url(self._redis_url, **self._redis_url_options)
            connection.ping()
        except redis.ConnectionError as e:
            raise ServiceUnavailable(f'Redis connection error to {display_url}: {_safe_msg(e)}') from None
        except redis.RedisError as e:
            raise ServiceUnavailable(f'Redis error ({type(e).__name__}) for {display_url}: {_safe_msg(e)}') from None

    def __repr__(self):
        """Return a unique identifier for this health check."""
        return f'redis:{self.redis_config_key}'


@dataclasses.dataclass(repr=False)
class NetBoxRedisCacheHealthCheck(BaseNetBoxRedisHealthCheck):
    """Health check for NetBox's caching Redis instance."""

    redis_config_key: str = 'caching'


@dataclasses.dataclass(repr=False)
class NetBoxRedisTasksHealthCheck(BaseNetBoxRedisHealthCheck):
    """Health check for NetBox's tasks/RQ Redis instance."""

    redis_config_key: str = 'tasks'
