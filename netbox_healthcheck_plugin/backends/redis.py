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

    @property
    def _connection_kwargs(self) -> dict:
        return self._connection.connection_pool.connection_kwargs

    def _target(self) -> str:
        """Describe the instance being checked, without credentials."""
        pool = self._connection.connection_pool
        if service_name := getattr(pool, 'service_name', None):
            return f'sentinel service {service_name!r}'
        kwargs = pool.connection_kwargs
        if path := kwargs.get('path'):
            return f'unix://{path}'
        return f'{kwargs.get("host")}:{kwargs.get("port")}/{kwargs.get("db", 0)}'

    def _scrub(self, message: str) -> str:
        """Strip the Redis password from a message, in case an exception echoes it back."""
        if password := self._connection_kwargs.get('password'):
            message = message.replace(password, 'REDACTED')
        return message

    def run(self):
        """Check Redis connectivity by issuing a PING command."""
        try:
            connection = self._connection
        except Exception as e:
            # Log the details for operators; the page only shows the exception type, since
            # connection settings may carry credentials.
            logger.exception("Unable to configure the '%s' Redis client", self.redis_config_key)
            raise ServiceUnavailable(
                f"Unable to configure the '{self.redis_config_key}' Redis client ({type(e).__name__})"
            ) from None

        try:
            connection.ping()
        except redis.ConnectionError as e:
            raise ServiceUnavailable(f'Redis connection error to {self._target()}: {self._scrub(str(e))}') from None
        except redis.RedisError as e:
            raise ServiceUnavailable(
                f'Redis error ({type(e).__name__}) for {self._target()}: {self._scrub(str(e))}'
            ) from None
        finally:
            if self.close_connection:
                connection.close()

    @property
    def labels(self) -> dict[str, str]:
        """Add the instance's host, port, db (or socket path, or Sentinel service) to the labels."""
        labels = super().labels | {'instance': self.redis_config_key}
        try:
            pool = self._connection.connection_pool
        except Exception:
            return labels
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
