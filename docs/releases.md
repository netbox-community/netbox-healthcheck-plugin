# Change Log

## v0.4.0

Released 2026-09-24.

### Breaking Changes
* The health check details now require login by default: anonymous requests get only the overall status (`200`/`500`, `OK`/`Unhealthy`), and anonymous browsers are redirected to the login page. Log in or send a NetBox API token for the per-check report, or set `login_required: False` in `PLUGINS_CONFIG` to show it to everyone. Probes that only look at the status code keep working without credentials; tools that parse the per-check JSON, text or OpenMetrics output need a token ([#1](https://github.com/netbox-community/netbox-healthcheck-plugin/issues/1))
* Require django-health-check >= 4.6 (fixes startup crash on NetBox 4.7 / Django 6.1: "The EMAIL_BACKEND setting is not available when MAILERS is defined") ([#22](https://github.com/netbox-community/netbox-healthcheck-plugin/issues/22))
* Default cache check is now `health_check.Cache`; `health_check.cache.backends.CacheBackend` and other 3.x check paths in `PLUGINS_CONFIG['checks']` are still accepted but log a deprecation warning
* Custom health checks must use the django-health-check 4.x API (`HealthCheck` dataclass with `run()`)
* JSON response keys are now each check's `repr` (e.g. `Database(alias='default')`) with `"OK"` or the error message as the value
* The memory check fails under different conditions: `health_check.contrib.psutil.backends.MemoryUsage` now maps to `health_check.contrib.psutil.Memory`, which by default fails at 90% memory used and has no free-memory floor (3.x failed only below 100 MB free). A host that runs above 90% memory used will start failing the check. To keep the 3.x behaviour, configure `("health_check.contrib.psutil.Memory", {"min_gibibytes_available": 0.1, "max_memory_usage_percent": None})`
* Redis health check errors show the exception type and target (e.g. `Redis ConnectionError for redis:6379/0`) but no longer the exception text, which may contain credentials; the details are logged instead
* Redis health checks now PING the client NetBox itself builds (django-rq's for `tasks`, django-redis's for `caching`) instead of building their own URL from `REDIS`; they report unavailable, instead of falling back to `localhost:6379`, when that client can't be configured. The `build_redis_url_from_config()` and `build_redis_url_options()` helpers were removed

### Enhancements
* Redis health checks support every connection option NetBox does: Redis Sentinel (`SENTINELS` / `SENTINEL_SERVICE`), `URL` (including Unix sockets) and `KWARGS`
* Redis health checks add `redis_instance`, `host`, `port` and `db` labels (`path` for Unix sockets, `service` for Sentinel) to the OpenMetrics output
* Checks accept options as `(path, {options})` pairs in `PLUGINS_CONFIG['checks']`, replacing django-health-check 3.x's `HEALTH_CHECK` settings ([#12](https://github.com/netbox-community/netbox-healthcheck-plugin/issues/12))
* The django-health-check 3.x psutil paths (`health_check.contrib.psutil.backends.DiskUsage` / `MemoryUsage`) map to `health_check.contrib.psutil.Disk` / `Memory`, and 3.x paths are also remapped inside `(path, options)` pairs. A warning is logged at startup if the 3.x `HEALTH_CHECK` setting (e.g. `DISK_USAGE_MAX`, `MEMORY_MIN`) is still set, since its thresholds are no longer applied
* `PLUGINS_CONFIG['checks']` is validated at startup; an invalid entry raises `ImproperlyConfigured` instead of failing every health check request with a 500
* Document the Storage, Mail, DNS and psutil checks, OpenMetrics labels, and the always-200 status of the OpenMetrics and feed formats

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

Released 2024-05-06.

* Updates for NetBox v4.0

---

## v0.1.3

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
