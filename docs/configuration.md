# Configuration

The NetBox HealthCheck Plugin can be customized through NetBox's `PLUGINS_CONFIG` settings.

## Basic Configuration

At minimum, the plugin needs to be enabled in your `configuration.py`:

```python
PLUGINS = ['netbox_healthcheck_plugin']

PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {}
}
```

This uses the default configuration with all built-in health checks enabled.

## Customizing Health Checks

You can control which health checks run by specifying the `checks` parameter:

```python
PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {
        "checks": [
            "health_check.Database",
            "health_check.cache.backends.CacheBackend",
            "netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck",
            "netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck",
        ]
    }
}
```

## Available Health Checks

### Built-in Checks

These health checks are provided by the [django-health-check](https://github.com/revsys/django-health-check) library:

#### `health_check.Database`

Verifies PostgreSQL database connectivity by performing a simple database query.

**What it checks:**
- Database server is accessible
- Database authentication succeeds
- Basic database operations work

#### `health_check.cache.backends.CacheBackend`

Tests Django cache framework operations (set/get) using NetBox's configured cache backend (typically Redis).

**What it checks:**
- Cache backend is accessible
- Can write to cache
- Can read from cache

### Plugin-Provided Checks

These custom health checks are specifically designed for NetBox's Redis configuration:

#### `netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck`

Directly checks the Redis instance used for caching.

**What it checks:**
- Redis caching instance is accessible
- Can execute Redis PING command
- Reads configuration from NetBox's `REDIS['caching']` settings

#### `netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck`

Directly checks the Redis instance used for the RQ task queue.

**What it checks:**
- Redis tasks instance is accessible
- Can execute Redis PING command
- Reads configuration from NetBox's `REDIS['tasks']` settings

## Adding Custom Health Checks

You can add your own health checks or checks from other plugins:

```python
PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {
        "checks": [
            # Default checks
            "health_check.Database",
            "health_check.cache.backends.CacheBackend",
            "netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck",
            "netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck",

            # Custom check from your plugin
            "my_custom_plugin.health.CustomHealthCheck",
        ]
    }
}
```

## Redis Configuration

The plugin automatically reads Redis configuration from NetBox's settings. No additional configuration is needed.

## Monitoring Integration

### JSON Response Format

For programmatic access, request the health check endpoint with `Accept: application/json`:

```bash
curl -H "Accept: application/json" https://netbox.example.com/plugins/netbox_healthcheck_plugin/healthcheck/
```

Response format:

```json
{
  "status": "working",
  "checks": {
    "Database": "working",
    "CacheBackend": "working",
    "NetBoxRedisCacheHealthCheck": "working",
    "NetBoxRedisTasksHealthCheck": "working"
  }
}
```

### HTTP Status Codes

- `200 OK` - All health checks passed
- `500 Internal Server Error` - One or more health checks failed

## Creating Custom Health Checks

To create your own health check:

1. Create a new class extending `health_check.backends.BaseHealthCheckBackend`:

```python
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable

class MyCustomHealthCheck(BaseHealthCheckBackend):
    #: The status endpoints will respond with a 200 status code
    #: even if the check errors.
    critical_service = False

    def check_status(self):
        # Perform your health check logic
        try:
            # Example: check external API
            response = requests.get('https://api.example.com/status', timeout=5)
            if response.status_code != 200:
                self.add_error(ServiceUnavailable("API returned non-200 status"))
        except Exception as e:
            self.add_error(ServiceUnavailable("API is unreachable"), e)

    def identifier(self):
        return "MyCustomCheck"
```

2. Add to your plugin configuration:

```python
PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {
        "checks": [
            "health_check.Database",
            "health_check.cache.backends.CacheBackend",
            "netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck",
            "netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck",
            "my_plugin.health.MyCustomHealthCheck",
        ]
    }
}
```

For more details on creating health checks, see the [django-health-check documentation](https://django-health-check.readthedocs.io/).

## Next Steps

- [Installation Guide](installation.md) - Install the plugin
- [Changelog](changelog.md) - See what's new
- [Contributing](contributing.md) - Help improve the plugin
