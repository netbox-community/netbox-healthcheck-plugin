# Changelog

## 0.3.0 (2026-02-06)

### Breaking Changes
* Minimum Python version increased to 3.12 (NetBox 4.5+ requirement)
* Minimum NetBox version increased to 4.5.0
* Require django-health-check >= 3.23
* **Redis Configuration Change:** Redis health checks now read directly from NetBox's `REDIS` configuration dict, rather than requiring a separate `REDIS_URL` Django setting
* Development tooling migrated from black + flake8 to ruff

### Features
* Add support for Python 3.12, 3.13, and 3.14
* Add support for NetBox 4.5+
* Replace `health_check.contrib.redis` with custom NetBox Redis health check backends
* Add separate health checks for both Redis instances: `caching` and `tasks`
* Add comprehensive ruff configuration for linting and formatting
* Add pytest configuration to pyproject.toml
* Add extensive test suite with Redis backend tests and plugin structure verification

### Refactoring
* Migrate off deprecated django-health-check APIs ahead of 4.x removal:
  * `BaseHealthCheckBackend` → `HealthCheck` base class
  * `MainView` → `HealthCheckView` with explicit `checks` list
  * `identifier()` → `__repr__()`
  * `add_error()` → raised exceptions
  * Remove `plugin_dir` registry, `health_check.db`, and `health_check.contrib.migrations`

### Bug Fixes
* Fix deprecated Django import (django.conf.urls → django.urls)
* Fix incorrect version string in PluginConfig
* Remove unused imports from views.py and navigation.py

### Dependencies
* Update django-health-check to >= 3.23.0, <4
* Add redis >= 4.0 for Redis health check backends
* Update pytest to >= 8.3.0
* Add pytest-django >= 4.9.0 for better Django testing support
* Replace black with ruff for code formatting
* Replace flake8 with ruff for linting

### Documentation
* Update compatibility matrix with Python version information
* Add detailed Redis health check configuration documentation
* Add important note about Redis configuration changes in 0.3.0
* Enhance README with detailed feature descriptions
* Add development workflow documentation for ruff
* Update CLAUDE.md with modernization notes and breaking changes

## 0.2.0 (2024-05006)

* Updates for NetBox v4.0

## 0.1.2 (2024-04-08)

* Fix django-health-check dependency in pyproject.toml

## 0.1.2 (2024-04-05)

* General cleanup

## 0.1.0 (2023-01-18)

* First release on PyPI.
