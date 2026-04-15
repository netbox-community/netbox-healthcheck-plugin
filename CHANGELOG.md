# Changelog

## Unreleased

### Breaking Changes
* Require `django-health-check >= 4.2.2` — v3 is no longer supported
* Removed the `NetBoxRedisHealthCheck` backwards-compatibility alias (use `NetBoxRedisCacheHealthCheck`)
* Default `checks` path for the cache backend changed from `health_check.cache.backends.CacheBackend` to `health_check.Cache`. Users who pinned `checks` in `PLUGINS_CONFIG` must update it.
* `health_check.cache` is no longer registered as a Django app; only `health_check` is installed.

### Features
* Redis password is URL-encoded when constructing the connection URL, so passwords containing special characters no longer break the connection ([#20](https://github.com/netbox-community/netbox-healthcheck-plugin/pull/20) by [@tacerus](https://github.com/tacerus)).

### Internal
* `BaseNetBoxRedisHealthCheck` is now a dataclass, and `check_status` has been renamed to `run` to match django-health-check v4's API.

## 0.3.0 (2026-02-06)

### Breaking Changes
* Minimum NetBox version increased to 4.5.0
* Require django-health-check >= 3.23
* Development tooling migrated from black + flake8 to ruff

### Features
* Add support for NetBox 4.5+
* Replace `health_check.contrib.redis` with custom NetBox Redis health check backends
* Add separate health checks for both Redis instances: `caching` and `tasks`
* Add Django cache framework health check (tests cache set/get operations)
* **Make health checks configurable via `PLUGINS_CONFIG['checks']` parameter**
* Add comprehensive ruff configuration for linting and formatting
* Add extensive test suite with Redis backend tests and plugin structure verification
* Update documentation

### Notes
* Migrations health check (`health_check.contrib.migrations`) was removed in django-health-check 3.23+ and is no longer available.

## 0.2.0 (2024-05006)

* Updates for NetBox v4.0

## 0.1.2 (2024-04-08)

* Fix django-health-check dependency in pyproject.toml

## 0.1.2 (2024-04-05)

* General cleanup

## 0.1.0 (2023-01-18)

* First release on PyPI.
