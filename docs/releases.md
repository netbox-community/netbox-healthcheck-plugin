# Change Log

## v0.4.0

Released 2026-09-24.

### Breaking Changes
* Require django-health-check >= 4.6 (fixes startup crash on NetBox 4.7 / Django 6.1: "The EMAIL_BACKEND setting is not available when MAILERS is defined") ([#22](https://github.com/netbox-community/netbox-healthcheck-plugin/issues/22))
* Default cache check is now `health_check.Cache`; `health_check.cache.backends.CacheBackend` and other 3.x check paths in `PLUGINS_CONFIG['checks']` are still accepted but log a deprecation warning
* Custom health checks must use the django-health-check 4.x API (`HealthCheck` dataclass with `run()`)
* JSON response keys are now each check's `repr` (e.g. `Database(alias='default')`) with `"OK"` or the error message as the value
* Redis health checks now report unavailable when `REDIS['caching']` or `REDIS['tasks']` is missing, instead of warning and falling back to `localhost:6379`

### Bug Fixes
* URL-encode the Redis username and password so special characters (including `/`) no longer break the connection ([#20](https://github.com/netbox-community/netbox-healthcheck-plugin/pull/20) by [@tacerus](https://github.com/tacerus), [#21](https://github.com/netbox-community/netbox-healthcheck-plugin/pull/21) by [@RangerRick](https://github.com/RangerRick))
* Redis passwords are no longer exposed in error messages or chained exceptions, and username-only URLs are no longer mangled when masked ([#21](https://github.com/netbox-community/netbox-healthcheck-plugin/pull/21))
* Only Redis errors are reported as a failed Redis check; unexpected exceptions propagate to django-health-check's handler ([#21](https://github.com/netbox-community/netbox-healthcheck-plugin/pull/21))

---

## v0.3.0

Released 2026-02-06.

### Breaking Changes
* Minimum NetBox version increased to 4.5.0
* Require django-health-check >= 3.23
* Development tooling migrated from black + flake8 to ruff

### Enhancements
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

---

## v0.2.0

Released 2024-05006.

* Updates for NetBox v4.0

---

## v0.1.2

Released 2024-04-08.

* Fix django-health-check dependency in pyproject.toml

---

## v0.1.2

Released 2024-04-05.

* General cleanup

---

## v0.1.0

Released 2023-01-18.

* First release on PyPI.
