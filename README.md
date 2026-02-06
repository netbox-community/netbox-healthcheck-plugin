# NetBox HealthCheck Plugin

NetBox plugin for HealthCheck.

NetBox provides health check monitors that can be queried to make sure that the service is running in good condition.

NetBox exposes metrics at the `/healthcheck` HTTP endpoint under the plugin, e.g. `https://netbox.local/plugins/netbox_healthcheck_plugin/healthcheck/`. It allows monitor conditions via HTTP(S), with responses available in HTML and JSON formats.

* Free software: Apache-2.0
* Documentation: https://netbox-community.github.io/netbox-healthcheck-plugin/


## Features

This plugin provides the following health checks:

- **Database** - Verifies PostgreSQL database connectivity
- **Migrations** - Checks for pending database migrations
- **Redis Cache** - Verifies connectivity to the caching Redis instance
- **Redis Tasks** - Verifies connectivity to the tasks/RQ Redis instance

Additional capabilities:
- HTTP/JSON response formats for external monitoring
- NetBox-integrated UI with styled health check display
- Extensible through django-health-check's plugin system

### Redis Health Checks

**NOTE:** Previous versions of this plugin used a `REDIS_URL` setting for connectivity, but as of `0.3.0` it reads the Redis configuration directly from NetBox's settings.

NetBox uses two Redis instances:
- `caching` - Used for Django cache operations
- `tasks` - Used for the RQ task queue (background workers)

Both are checked automatically. The configuration supports:
- `HOST`, `PORT`, `DATABASE` - Connection parameters
- `USERNAME`, `PASSWORD` - Authentication (optional)
- `SSL`, `INSECURE_SKIP_TLS_VERIFY`, `CA_CERT_PATH` - TLS settings (optional)

## Compatibility

| NetBox Version | Plugin Version | Python Version    |
|----------------|----------------|-------------------|
|   3.4 - 3.7    |      0.1.x     | 3.10, 3.11, 3.12 |
|   4.0 - 4.4    |      0.2.0     | 3.10, 3.11, 3.12 |
|   4.5+         |      0.3.0     | 3.12, 3.13, 3.14 |

**Current Version:** 0.3.0

**Supported Dependencies:**
- NetBox: >= 4.5.0
- Python: >= 3.12.0
- django-health-check: >= 3.23.0, < 4
- redis: >= 4.0

## Installing

For adding to a NetBox Docker setup see
[the general instructions for using netbox-docker with plugins](https://github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins).

While this is still in development and not yet on pypi you can install with pip:

```bash
pip install git+https://github.com/netbox-community/netbox-healthcheck-plugin
```

or by adding to your `local_requirements.txt` or `plugin_requirements.txt` (netbox-docker):

```bash
git+https://github.com/netbox-community/netbox-healthcheck-plugin
```

Enable the plugin in `/opt/netbox/netbox/netbox/configuration.py`,
 or if you use netbox-docker, your `/configuration/plugins.py` file :

```python
PLUGINS = [
    'netbox_healthcheck_plugin'
]

PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {},
}
```

## Development

This plugin uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
# Install development dependencies
pip install -e ".[test]"

# Run linting and formatting
ruff check .
ruff format .

# Run tests
pytest

# Install pre-commit hooks
pre-commit install
```

## Setting up Monitoring

NetBox makes use of the [django-health-check](https://github.com/revsys/django-health-check) library, more information on setting up monitors can be found at [Setting up Monitoring](https://django-health-check.readthedocs.io/en/latest/readme.html#setting-up-monitoring):

## Credits

Based on the NetBox plugin tutorial:

- [demo repository](https://github.com/netbox-community/netbox-plugin-demo)
- [tutorial](https://github.com/netbox-community/netbox-plugin-tutorial)

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [`netbox-community/cookiecutter-netbox-plugin`](https://github.com/netbox-community/cookiecutter-netbox-plugin) project template.
