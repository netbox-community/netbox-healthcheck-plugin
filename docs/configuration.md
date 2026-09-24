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

### Check Options

Each check's settings are passed to it as keyword arguments. To set them, give the check as a `(path, options)` pair instead of a plain path:

```python
PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {
        "checks": [
            "health_check.Database",
            ("health_check.Database", {"alias": "replica"}),  # a second DATABASES entry
            "health_check.Cache",
            "netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck",
            "netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck",
            ("health_check.contrib.psutil.Disk", {"path": "/opt/netbox/netbox/media", "max_disk_usage_percent": 85}),
        ]
    }
}
```

This replaces django-health-check 3.x's global `HEALTH_CHECK` settings dict, which is no longer read. The options each check accepts are listed in the [django-health-check checks reference](https://codingjoe.dev/django-health-check/checks/).

## Available Health Checks

### Built-in Checks

These health checks are provided by the [django-health-check](https://github.com/codingjoe/django-health-check) library. `health_check.Database` and `health_check.Cache` are enabled by default; add the others to `checks` as needed.

#### `health_check.Database`

Verifies PostgreSQL database connectivity by performing a simple database query.

**What it checks:**
- Database server is accessible
- Database authentication succeeds
- Basic database operations work

**Options:** `alias` (default `"default"`), for checking another `DATABASES` entry.

#### `health_check.Cache`

Tests Django cache framework operations (set/get) using NetBox's configured cache backend (typically Redis).

**What it checks:**
- Cache backend is accessible
- Can write to cache
- Can read from cache

#### `health_check.Storage`

Saves, reads back and deletes a small file in NetBox's default file storage (the media root, or the backend configured in `STORAGES`), where uploaded images and attachments live.

**Options:** `alias` (default `"default"`).

#### `health_check.Mail`

Opens a connection to NetBox's mail server (the `EMAIL` settings) without sending a message. On NetBox 4.7 this reads Django 6.1's `MAILERS` setting.

**Options:** `alias` (default `"default"`), `timeout`.

#### `health_check.DNS`

Resolves a hostname (by default the server's own) through the system's nameservers.

**Options:** `hostname`, `nameservers`, `record_type` (e.g. `"A"` or `"AAAA"`), `timeout`.

#### `health_check.contrib.psutil.Disk` / `health_check.contrib.psutil.Memory`

Fail when disk usage or memory usage crosses a threshold. They need the `psutil` extra:

```bash
pip install "django-health-check[psutil]"
```

**Options:** `Disk`: `path`, `max_disk_usage_percent` (default 90). `Memory`: `max_memory_usage_percent` (default 90), `min_gibibytes_available`.

### Plugin-Provided Checks

These checks PING the two Redis instances in NetBox's `REDIS` setting. They don't read `REDIS` directly. Instead they use the client NetBox builds from it (django-rq's for `tasks`, django-redis's for `caching`), so they connect exactly as NetBox does. That includes `HOST`/`PORT`, `URL` (including Unix sockets), `SENTINELS`, `SSL`, `CA_CERT_PATH` and `KWARGS`.

#### `netbox_healthcheck_plugin.backends.redis.NetBoxRedisCacheHealthCheck`

Directly checks the Redis instance used for caching.

**What it checks:**
- Redis caching instance (`REDIS['caching']`) is accessible
- Can execute Redis PING command

#### `netbox_healthcheck_plugin.backends.redis.NetBoxRedisTasksHealthCheck`

Directly checks the Redis instance used for the RQ task queue.

**What it checks:**
- Redis tasks instance (`REDIS['tasks']`) is accessible
- Can execute Redis PING command

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

The plugin uses NetBox's own `REDIS` configuration. No additional configuration is needed.

## Monitoring Integration

### JSON Response Format

For programmatic access, request the health check endpoint with `Accept: application/json`:

```bash
curl -H "Accept: application/json" https://netbox.example.com/plugins/netbox_healthcheck_plugin/healthcheck/
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

### OpenMetrics (Prometheus)

`?format=openmetrics` (or `Accept: application/openmetrics-text`) returns a `django_health_check_status` gauge and a `django_health_check_response_time_seconds` gauge per check. The Redis checks are labelled with the instance they check, so the two can be told apart:

```text
django_health_check_status{check="NetBoxRedisCacheHealthCheck",instance="caching",host="redis",port="6379",db="1"} 1
django_health_check_status{check="NetBoxRedisTasksHealthCheck",instance="tasks",host="redis",port="6379",db="0"} 1
```

A Unix socket is labelled `path` in place of `host`/`port`, and a Sentinel deployment is labelled `service` (the `SENTINEL_SERVICE`). Credentials are never included.

### HTTP Status Codes

For the HTML, JSON and plain text formats:

- `200 OK` - All health checks passed
- `500 Internal Server Error` - One or more health checks failed

The OpenMetrics, RSS and Atom formats always return `200 OK`, because Prometheus and feed readers expect it. Read the check status from the response body instead.

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
