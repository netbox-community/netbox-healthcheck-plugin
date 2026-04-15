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
            "health_check.Cache",
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

#### `health_check.Cache`

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
            "health_check.Cache",
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

Response format (v4 returns a flat map keyed by each check's `repr`):

```json
{
  "Database(alias='default')": "OK",
  "Cache(alias='default')": "OK",
  "redis:caching": "OK",
  "redis:tasks": "OK"
}
```

Failed checks show the error message instead of `OK`.

### HTTP Status Codes

- `200 OK` - All health checks passed
- `500 Internal Server Error` - One or more health checks failed

## Creating Custom Health Checks

To create your own health check:

1. Create a new dataclass extending `health_check.HealthCheck` and implement `run`:

```python
import dataclasses

import requests
from health_check import HealthCheck
from health_check.exceptions import ServiceUnavailable


@dataclasses.dataclass
class MyCustomHealthCheck(HealthCheck):
    url: str = "https://api.example.com/status"

    def run(self):
        # Raise ServiceUnavailable to signal failure. Returning None signals success.
        try:
            response = requests.get(self.url, timeout=5)
        except requests.RequestException as e:
            raise ServiceUnavailable("API is unreachable") from e
        if response.status_code != 200:
            raise ServiceUnavailable("API returned non-200 status")

    def __repr__(self):
        return f"MyCustomCheck({self.url})"
```

2. Add to your plugin configuration:

```python
PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {
        "checks": [
            "health_check.Database",
            "health_check.Cache",
            "netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck",
            "netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck",
            "my_plugin.health.MyCustomHealthCheck",
        ]
    }
}
```

For more details on creating health checks, see the [django-health-check documentation](https://codingjoe.dev/django-health-check/).

## Next Steps

- [Installation Guide](installation.md) - Install the plugin
- [Changelog](changelog.md) - See what's new
- [Contributing](contributing.md) - Help improve the plugin
