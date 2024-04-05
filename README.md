# NetBox HealthCheck Plugin

NetBox plugin for HealthCheck.

NetBox provides health check monitors that can be queried to make sure that the service is running in good condition.  

NetBox exposes metrics at the `/healthcheck` HTTP endpoint, e.g. `https://netbox.local/healthcheck`. It allows monitor conditions via HTTP(S), with responses available in HTML and JSON formats.

* Free software: Apache-2.0
* Documentation: https://netbox-community.github.io/netbox-healthcheck-plugin/


## Features

The features the plugin provides should be listed here.

## Compatibility

| NetBox Version | Plugin Version |
|----------------|----------------|
|   3.4 - 3.7    |      0.1.0     |
|   3.4 - 3.7    |      0.1.2     |

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

## Setting up Monitoring

NetBox makes use of the [django-health-check](https://github.com/revsys/django-health-check) library, more information on setting up monitors can be found at [Setting up Monitoring](https://django-health-check.readthedocs.io/en/latest/readme.html#setting-up-monitoring):

## Credits

Based on the NetBox plugin tutorial:

- [demo repository](https://github.com/netbox-community/netbox-plugin-demo)
- [tutorial](https://github.com/netbox-community/netbox-plugin-tutorial)

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [`netbox-community/cookiecutter-netbox-plugin`](https://github.com/netbox-community/cookiecutter-netbox-plugin) project template.
