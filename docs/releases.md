# Change Log

## v0.4.0

Released 2026-10-06.

!!! warning "Login Required by Default"
    Anonymous requests now get only the overall status (`200`/`500`); the per-check report requires a NetBox login or API token. Status-code probes keep working, but tools that parse the JSON, text or OpenMetrics output need a token. Set `login_required: False` to restore the previous behaviour. See [Authentication](configuration.md#authentication).

!!! warning "django-health-check 4.x"
    This release requires django-health-check >= 4.6. Custom checks must use the 4.x `HealthCheck` API, JSON keys are now each check's `repr`, and the 3.x `HEALTH_CHECK` settings are no longer read. The psutil memory check now fails at 90% memory used by default. See [Check Options](configuration.md#check-options) for migrating thresholds.

### Breaking Changes

* [#1](https://github.com/netbox-community/netbox-healthcheck-plugin/issues/1) - Require login (session or API token) for the per-check report by default
* [#22](https://github.com/netbox-community/netbox-healthcheck-plugin/issues/22) - Require django-health-check >= 4.6, fixing a startup crash on NetBox 4.7
* Redis checks use the clients NetBox builds and no longer fall back to `localhost:6379`; `build_redis_url_from_config()` and `build_redis_url_options()` were removed
* Redis check errors no longer include the exception text, which may contain credentials

### Enhancements

* Add support for NetBox 4.7
* [#12](https://github.com/netbox-community/netbox-healthcheck-plugin/issues/12) - Accept per-check options as `(path, {options})` pairs in `PLUGINS_CONFIG['checks']`
* Support Redis Sentinel, `URL` (including Unix sockets) and `KWARGS` in the Redis checks
* Add `redis_instance`, `host`, `port` and `db` labels to the Redis checks' OpenMetrics output
* Map django-health-check 3.x check paths to their 4.x equivalents, logging a deprecation warning
* Validate `PLUGINS_CONFIG['checks']` at startup

### Bug Fixes

* [#20](https://github.com/netbox-community/netbox-healthcheck-plugin/pull/20), [#21](https://github.com/netbox-community/netbox-healthcheck-plugin/pull/21) - Fix Redis connections when the username or password contains special characters (thanks [@tacerus](https://github.com/tacerus), [@RangerRick](https://github.com/RangerRick))
* [#21](https://github.com/netbox-community/netbox-healthcheck-plugin/pull/21) - Prevent Redis passwords from appearing in error messages
* [#21](https://github.com/netbox-community/netbox-healthcheck-plugin/pull/21) - Report only Redis errors as Redis check failures

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
