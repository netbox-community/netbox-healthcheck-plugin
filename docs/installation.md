# Installation

This guide covers how to install the NetBox HealthCheck Plugin in various NetBox environments.

## Requirements

Before installing, ensure you meet the following requirements:

- NetBox >= 4.5.0
- Python >= 3.12.0
- Redis (for NetBox's cache and task queue)
- PostgreSQL (NetBox's database)

## Installation Methods

### Using pip

The simplest way to install the plugin:

```bash
pip install netbox-healthcheck-plugin
```

### Using netbox-docker

If you're using [netbox-docker](https://github.com/netbox-community/netbox-docker):

1. Add to your `plugin_requirements.txt`:

   ```
   netbox-healthcheck-plugin
   ```

2. Rebuild your NetBox container:

   ```bash
   docker compose build --no-cache netbox
   docker compose up -d
   ```

### From Source

For development or testing the latest changes:

```bash
git clone https://github.com/netbox-community/netbox-healthcheck-plugin.git
cd netbox-healthcheck-plugin
pip install -e .
```

## Configuration

After installation, enable the plugin in your NetBox configuration file.

### Basic Configuration

Add to `/opt/netbox/netbox/netbox/configuration.py` (or `/configuration/plugins.py` for netbox-docker):

```python
PLUGINS = [
    'netbox_healthcheck_plugin'
]

PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {}
}
```

### Restart NetBox

After configuration, restart NetBox services:

=== "Standard Installation"

    ```bash
    sudo systemctl restart netbox netbox-rq
    ```

=== "netbox-docker"

    ```bash
    docker compose restart netbox netbox-worker
    ```

## Verification

Verify the installation by visiting the health check endpoint:

```
https://your-netbox-instance/plugins/netbox_healthcheck_plugin/healthcheck/
```

You should see a page displaying health check results for:

- ✅ Database connectivity
- ✅ Cache operations
- ✅ Redis cache instance
- ✅ Redis tasks instance

## Troubleshooting

### Plugin Not Found

If NetBox reports the plugin is not installed:

1. Verify the plugin is installed in the correct Python environment:
   ```bash
   pip list | grep netbox-healthcheck-plugin
   ```

2. Ensure NetBox is using the same Python environment where the plugin was installed

### Import Errors

If you see import errors:

1. Check that all dependencies are installed:
   ```bash
   pip install django-health-check>=3.23.0 redis>=4.0
   ```

2. Verify your NetBox version meets the minimum requirement (>= 4.5.0)

### Health Check Failures

If health checks are failing:

- **Database**: Verify PostgreSQL is running and NetBox can connect
- **Cache**: Check Redis is running and configured correctly in NetBox's `REDIS` settings
- **Redis instances**: Verify both `caching` and `tasks` Redis instances are accessible

For more configuration options, see the [Configuration](configuration.md) guide.

## Next Steps

- [Configuration Options](configuration.md) - Customize which health checks run
- [Contributing](contributing.md) - Help improve the plugin
