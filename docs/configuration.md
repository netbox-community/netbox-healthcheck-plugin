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

## Authentication

By default the health check page requires the same login as the rest of NetBox. A request is let through if it comes
from a logged-in session or carries a NetBox API token, so monitoring tools can authenticate with a token:

```bash
curl -H "Authorization: Bearer nbt_<key>.<token>" \
  "https://netbox.example.com/plugins/netbox_healthcheck_plugin/healthcheck/?format=json"
```

Any user's token works and no particular permission is needed, so a dedicated low-privilege user with a read-only
token is enough.

Anonymous browser requests (those that prefer `text/html`) are redirected to the login page. Every other anonymous
request, such as a `?format=` request, curl, or a monitoring probe, gets `401 Unauthorized` rather than a redirect,
because probes like Kubernetes' treat any 3xx response as healthy. An invalid token gets `403 Forbidden`. If NetBox's own
`LOGIN_REQUIRED` is `False`, the page is open to everyone, like the rest of NetBox.

Checking the token or session needs the database (and the session store), so while the database is down an
authenticated request fails with a generic `500` error before any check runs, instead of the usual report of which
check failed. The request still fails, but without detail.

For load balancer health checks and Kubernetes liveness or readiness probes, set `login_required` to `False` so the
probe needs no credentials and always gets the full report:

```python
PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {
        "login_required": False,
    }
}
```

Failing checks report error messages that can include internal hostnames and ports, so consider limiting who can reach
the path (for example at your reverse proxy) when login is not required.

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

For programmatic access, request the health check endpoint with `Accept: application/json` (plus an API token unless
`login_required` is `False`; see [Authentication](#authentication)):

```bash
curl -H "Accept: application/json" -H "Authorization: Bearer nbt_<key>.<token>" \
  https://netbox.example.com/plugins/netbox_healthcheck_plugin/healthcheck/
```

Response format (keys are each check's `repr`):

```json
{
  "Database(alias='default')": "OK",
  "Cache(alias='default')": "OK",
  "redis:caching": "OK",
  "redis:tasks": "OK"
}
```

A failing check reports its error message in place of `"OK"`. Plain text (`?format=text`), OpenMetrics (`?format=openmetrics`), RSS and Atom formats are also available.

### HTTP Status Codes

- `200 OK` - All health checks passed
- `500 Internal Server Error` - One or more health checks failed

## Creating Custom Health Checks

To create your own health check:

1. Create a dataclass extending `health_check.HealthCheck` and implement `run()`. Raise a `ServiceUnavailable` (or other `HealthCheckException`) to report a failure; `run()` may be sync or `async`:

```python
import dataclasses

import requests
from health_check import HealthCheck
from health_check.exceptions import ServiceUnavailable


@dataclasses.dataclass
class MyCustomHealthCheck(HealthCheck):
    url: str = 'https://api.example.com/status'

    def run(self):
        try:
            response = requests.get(self.url, timeout=5)
        except requests.RequestException as e:
            raise ServiceUnavailable('API is unreachable') from e
        if response.status_code != 200:
            raise ServiceUnavailable('API returned non-200 status')
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

For more details on creating health checks, see the [django-health-check documentation](https://django-health-check.readthedocs.io/).

## Next Steps

- [Quickstart](quickstart.md) - Install the plugin
- [Releases](releases.md) - See what's new
- [Contributing](development/contributing.md) - Help improve the plugin
