# NetBox HealthCheck Plugin

A [NetBox](https://github.com/netbox-community/netbox) plugin that provides comprehensive health monitoring for your NetBox installation.

[![Version](https://img.shields.io/pypi/v/netbox-healthcheck-plugin)](https://pypi.org/project/netbox-healthcheck-plugin/)
[![Python Versions](https://img.shields.io/pypi/pyversions/netbox-healthcheck-plugin)](https://pypi.org/project/netbox-healthcheck-plugin/)
[![License](https://img.shields.io/github/license/netbox-community/netbox-healthcheck-plugin)](https://github.com/netbox-community/netbox-healthcheck-plugin/blob/main/LICENSE)

## Features

This plugin integrates [django-health-check](https://github.com/revsys/django-health-check) with NetBox to provide health monitoring of critical services:

- **Database** - PostgreSQL connectivity and operations
- **Cache** - Django cache framework (Redis-backed)
- **Redis Instances** - Both caching and task queue Redis connections
- **Extensible** - Add custom health checks via configuration

Health status is exposed at `/plugins/netbox_healthcheck_plugin/healthcheck/` with both HTML and JSON response formats for integration with monitoring systems.

## Installation

```bash
pip install netbox-healthcheck-plugin
```

Add to your NetBox `configuration.py`:

```python
PLUGINS = ['netbox_healthcheck_plugin']

PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {}
}
```

Restart NetBox and visit: `https://your-netbox/plugins/netbox_healthcheck_plugin/healthcheck/`

## Compatibility

| NetBox Version | Plugin Version | Python Version    |
|----------------|----------------|-------------------|
| 4.5 - 4.7      | 0.4.0          | 3.12, 3.13, 3.14 |
| 4.5 - 4.6      | 0.3.0          | 3.12, 3.13, 3.14 |
| 4.0 - 4.4      | 0.2.0          | 3.10, 3.11, 3.12 |
| 3.4 - 3.7      | 0.1.x          | 3.10, 3.11, 3.12 |

See [COMPATIBILITY.md](https://github.com/netbox-community/netbox-healthcheck-plugin/blob/main/COMPATIBILITY.md) for detailed version information.

## Configuration

Customize which health checks run via `PLUGINS_CONFIG`:

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

You can add custom health checks or disable specific checks. See the [Configuration Guide](https://netbox-community.github.io/netbox-healthcheck-plugin/configuration/) for more options.

## Documentation

Full documentation is available at: https://netbox-community.github.io/netbox-healthcheck-plugin/

- [Quickstart](https://netbox-community.github.io/netbox-healthcheck-plugin/quickstart/)
- [Configuration Options](https://netbox-community.github.io/netbox-healthcheck-plugin/configuration/)
- [Contributing Guidelines](https://netbox-community.github.io/netbox-healthcheck-plugin/development/contributing/)
- [Releases](https://netbox-community.github.io/netbox-healthcheck-plugin/releases/)

## Development

Tests run inside a NetBox checkout using NetBox's test runner, with this repo's
`testing/configuration.py` (see [AGENTS.md](AGENTS.md) for the full setup):

```bash
pip install -e '.[dev,test]'
export NETBOX_CONFIGURATION=configuration PYTHONPATH="$PWD/testing"
python /path/to/netbox/netbox/manage.py test netbox_healthcheck_plugin.tests

pre-commit install           # lint/format hooks (ruff, djlint, codespell, yamllint)
pre-commit run --all-files
```

## Support

- **Issues**: [GitHub Issues](https://github.com/netbox-community/netbox-healthcheck-plugin/issues)
- **Discussions**: [GitHub Discussions](https://github.com/netbox-community/netbox-healthcheck-plugin/discussions)
- **Source**: [GitHub Repository](https://github.com/netbox-community/netbox-healthcheck-plugin)

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](https://github.com/netbox-community/netbox-healthcheck-plugin/blob/main/LICENSE) file for details.
