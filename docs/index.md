# NetBox HealthCheck Plugin

A [NetBox](https://github.com/netbox-community/netbox) plugin that provides comprehensive health monitoring for your NetBox installation.

[![Version](https://img.shields.io/pypi/v/netbox-healthcheck-plugin)](https://pypi.org/project/netbox-healthcheck-plugin/)
[![Python Versions](https://img.shields.io/pypi/pyversions/netbox-healthcheck-plugin)](https://pypi.org/project/netbox-healthcheck-plugin/)
[![License](https://img.shields.io/github/license/netbox-community/netbox-healthcheck-plugin)](https://github.com/netbox-community/netbox-healthcheck-plugin/blob/main/LICENSE)

## Overview

This plugin integrates [django-health-check](https://github.com/revsys/django-health-check) with NetBox to provide health monitoring of critical services:

- **Database** - PostgreSQL connectivity and operations
- **Cache** - Django cache framework (Redis-backed)
- **Redis Instances** - Both caching and task queue Redis connections
- **Extensible** - Add custom health checks via configuration

Health status is exposed at `/plugins/netbox_healthcheck_plugin/healthcheck/` with both HTML and JSON response formats for integration with monitoring systems.

## Features

### Built-in Health Checks

✅ **Database Connectivity** - Verifies PostgreSQL database is accessible
✅ **Cache Operations** - Tests Django cache set/get operations
✅ **Redis Cache Instance** - Monitors caching Redis connection
✅ **Redis Tasks Instance** - Monitors RQ task queue Redis connection

### Capabilities

- **NetBox-Integrated UI** - Styled health check page matching NetBox's design
- **JSON API** - Programmatic access for monitoring tools
- **Configurable Checks** - Enable/disable checks via `PLUGINS_CONFIG`
- **Custom Health Checks** - Add your own health checks easily
- **NetBox 4.5+ Support** - Built for modern NetBox versions

## Quick Start

### Installation

```bash
pip install netbox-healthcheck-plugin
```

### Configuration

Add to your NetBox `configuration.py`:

```python
PLUGINS = ['netbox_healthcheck_plugin']

PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {}
}
```

Restart NetBox and visit: `https://your-netbox/plugins/netbox_healthcheck_plugin/healthcheck/`

## Requirements

- NetBox >= 4.5.0
- Python >= 3.12
- Redis (for NetBox's cache and task queue)
- PostgreSQL (NetBox's database)

## Compatibility

| NetBox Version | Plugin Version | Python Version    |
|----------------|----------------|-------------------|
| 4.5+           | 0.3.0          | 3.12, 3.13, 3.14 |
| 4.0 - 4.4      | 0.2.0          | 3.10, 3.11, 3.12 |
| 3.4 - 3.7      | 0.1.x          | 3.10, 3.11, 3.12 |

See [COMPATIBILITY.md](https://github.com/netbox-community/netbox-healthcheck-plugin/blob/main/COMPATIBILITY.md) for detailed version information.

## Documentation

- [Installation Guide](installation.md)
- [Configuration Options](configuration.md)
- [Contributing Guidelines](contributing.md)
- [Changelog](changelog.md)

## Support

- **Issues**: [GitHub Issues](https://github.com/netbox-community/netbox-healthcheck-plugin/issues)
- **Discussions**: [GitHub Discussions](https://github.com/netbox-community/netbox-healthcheck-plugin/discussions)
- **Source**: [GitHub Repository](https://github.com/netbox-community/netbox-healthcheck-plugin)

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](https://github.com/netbox-community/netbox-healthcheck-plugin/blob/main/LICENSE) file for details.
