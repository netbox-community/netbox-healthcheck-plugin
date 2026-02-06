# Changelog

## 0.3.0 (2026-02-06)

### Breaking Changes
* Minimum Python version increased to 3.12 (NetBox 4.5+ requirement)
* Minimum NetBox version increased to 4.5.0
* Require django-health-check >= 3.23
* Development tooling migrated from black + flake8 to ruff

### Features
* Add support for Python 3.12, 3.13, and 3.14
* Add support for NetBox 4.5+
* Replace `health_check.contrib.redis` with custom NetBox Redis health check backends
* Add separate health checks for both Redis instances: `caching` and `tasks`
* Add Django cache framework health check (tests cache set/get operations)
* Add comprehensive ruff configuration for linting and formatting
* Add extensive test suite with Redis backend tests and plugin structure verification
* Update documentation

### Bug Fixes
* Remove unused imports from views.py and navigation.py

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
