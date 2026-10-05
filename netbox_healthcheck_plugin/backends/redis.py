"""
Redis health check backends for NetBox.

NetBox turns its REDIS configuration into two client configurations: the tasks
instance becomes django-rq's RQ_QUEUES and the caching instance becomes
django-redis's CACHES['default']. Rather than re-deriving a connection from
settings.REDIS, these checks ping the client those libraries build, so every
connection option NetBox supports (HOST/PORT, URL including Unix sockets,
SENTINELS, SSL, CA_CERT_PATH, KWARGS) is checked exactly as NetBox uses it.
"""

import dataclasses
import functools
import logging
import typing

import redis
from django.conf import settings
from health_check import HealthCheck
from health_check.exceptions import ServiceUnavailable
from redis.connection import parse_url

from netbox.constants import RQ_QUEUE_DEFAULT

logger = logging.getLogger('netbox_healthcheck_plugin')

# Connection pool kwargs that identify an instance; exposed as OpenMetrics labels.
# Never add 'password' or 'username' here.
LABEL_KWARGS = ('host', 'port', 'path', 'db')


@dataclasses.dataclass
class BaseNetBoxRedisHealthCheck(HealthCheck):
    """
    Base health check that PINGs one of NetBox's Redis instances.

    Subclasses set `redis_config_key` and implement `get_connection()`. Set
    `close_connection` to False when the client comes from a shared pool that
    must stay open.
    """

    redis_config_key: typing.ClassVar[str]
    close_connection: typing.ClassVar[bool] = True

    def get_connection(self) -> redis.Redis:
        """Return the Redis client NetBox uses for this instance."""
        raise NotImplementedError

    @functools.cached_property
    def _connection(self) -> redis.Redis:
        return self.get_connection()

    def _target(self) -> str:
        """Describe the instance being checked, without credentials."""
        pool = self._connection.connection_pool
        if service_name := getattr(pool, 'service_name', None):
            return f'sentinel service {service_name!r}'
        kwargs = pool.connection_kwargs
        if path := kwargs.get('path'):
            return f'unix://{path}'
        return f'{kwargs.get("host")}:{kwargs.get("port")}/{kwargs.get("db", 0)}'

    def run(self):
        """Check Redis connectivity by issuing a PING command."""
        # Error messages name the exception type and target only: exception text may echo
        # connection settings, including credentials. Operators get the detail in the log.
        try:
            connection = self._connection
        except Exception as e:
            logger.warning("Unable to configure the '%s' Redis client: %r", self.redis_config_key, e)
            raise ServiceUnavailable(
                f"Unable to configure the '{self.redis_config_key}' Redis client ({type(e).__name__}); "
                'see the NetBox log for details'
            ) from None

        try:
            connection.ping()
        except Exception as e:
            target = self._target()
            logger.warning("Redis check '%s' failed for %s: %r", self.redis_config_key, target, e)
            raise ServiceUnavailable(f'Redis {type(e).__name__} for {target}') from None
        finally:
            if self.close_connection:
                try:
                    connection.close()
                except Exception as e:
                    # Don't let a failed close mask the PING result.
                    logger.warning("Unable to close the '%s' Redis client: %r", self.redis_config_key, e)

    def _settings_labels(self) -> dict[str, str]:
        """
        Derive host/port/db (or path, or service) labels from settings.REDIS.

        Only used when the client can't be built, so a failing instance keeps the same
        series as a healthy one. Missing keys take NetBox's defaults (netbox/settings.py).
        """
        config = (getattr(settings, 'REDIS', None) or {}).get(self.redis_config_key)
        if not config:
            return {}
        if config.get('SENTINELS'):
            kwargs = {'service': config.get('SENTINEL_SERVICE', 'default'), 'db': config.get('DATABASE', 0)}
        elif url := config.get('URL'):
            try:
                kwargs = {key: value for key, value in parse_url(url).items() if key in LABEL_KWARGS}
            except Exception:
                return {}
        else:
            kwargs = {
                'host': config.get('HOST', 'localhost'),
                'port': config.get('PORT', 6379),
                'db': config.get('DATABASE', 0),
            }
        return {key: str(value) for key, value in kwargs.items() if value is not None}

    @property
    def labels(self) -> dict[str, str]:
        """Add the instance's host, port, db (or socket path, or Sentinel service) to the labels."""
        # 'redis_instance', not 'instance': Prometheus sets 'instance' to the scrape target and
        # would rename ours to 'exported_instance'.
        labels = super().labels | {'redis_instance': self.redis_config_key}
        try:
            pool = self._connection.connection_pool
        except Exception:
            return labels | self._settings_labels()
        keys = LABEL_KWARGS
        if service_name := getattr(pool, 'service_name', None):
            # Sentinel resolves the master at connect time; django-redis leaves the service
            # name in 'host', so only the service and db identify the instance.
            labels['service'] = str(service_name)
            keys = ('db',)
        labels |= {key: str(value) for key in keys if (value := pool.connection_kwargs.get(key)) is not None}
        return labels

    def __repr__(self):
        """Return a stable identifier for this health check (used as the JSON key)."""
        return f'redis:{self.redis_config_key}'


@dataclasses.dataclass(repr=False)
class NetBoxRedisCacheHealthCheck(BaseNetBoxRedisHealthCheck):
    """Health check for NetBox's caching Redis instance (REDIS['caching'])."""

    redis_config_key = 'caching'
    # django-redis hands out a client backed by the cache's shared connection pool.
    close_connection = False

    def get_connection(self) -> redis.Redis:
        from django_redis import get_redis_connection

        return get_redis_connection('default')


@dataclasses.dataclass(repr=False)
class NetBoxRedisTasksHealthCheck(BaseNetBoxRedisHealthCheck):
    """Health check for NetBox's tasks/RQ Redis instance (REDIS['tasks'])."""

    redis_config_key = 'tasks'

    def get_connection(self) -> redis.Redis:
        from django_rq.queues import get_redis_connection

        return get_redis_connection(settings.RQ_QUEUES[RQ_QUEUE_DEFAULT])


# Backwards compatibility alias
NetBoxRedisHealthCheck = NetBoxRedisCacheHealthCheck
