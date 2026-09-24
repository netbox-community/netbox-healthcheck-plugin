# Compatibility

This document tracks the supported NetBox and Python versions for each
release of NetBox HealthCheck Plugin.

| Plugin Version | Minimum NetBox Version | Maximum NetBox Version | Minimum Python |
|----------------|------------------------|------------------------|----------------|
| 0.4.0 | 4.5.0 | 4.7.99 | 3.12 |
| 0.3.0 | 4.5.0 | 4.6.x | 3.12 |
| 0.2.0 | 4.0.0 | 4.4.x | 3.10 |
| 0.1.4 | 3.4.0 | 3.7.x | 3.10 |
| 0.1.3 | 3.4.0 | 3.7.x | 3.10 |
| 0.1.2 | 3.4.0 | 3.7.x | 3.10 |
| 0.1.0 | 3.4.0 | 3.7.x | 3.10 |

## Breaking Changes

### Version 0.4.0
- **django-health-check >= 4.6 required** - Fixes startup failure on NetBox 4.7+ (Django 6.1)
- **Custom health checks** must use the django-health-check 4.x API (`HealthCheck` dataclass with `run()`)
- **JSON response keys** are now each check's `repr` (e.g. `Database(alias='default')`)
- **Maximum NetBox version declared** - `max_version = '4.7.99'`; NetBox refuses to load the plugin on newer releases until a release raises the ceiling

### Version 0.3.0
- **Minimum Python version increased to 3.12** - Required by NetBox 4.5+
- **Minimum NetBox version increased to 4.5.0** - Leverages NetBox 4.5 plugin improvements
- **Redis configuration change** - Now reads from NetBox's native `REDIS` settings dict instead of separate `REDIS_URL` setting
- **django-health-check >= 3.23 required** - Uses modern API (deprecated APIs removed)
- **Development tooling changed** - Replaced black + flake8 with ruff

### Version 0.2.0
- **Minimum NetBox version increased to 4.0** - Updated for NetBox 4.0 plugin API changes
- **Python 3.9 no longer supported** - Minimum Python version is 3.10

### Version 0.1.x
- Initial releases supporting NetBox 3.4-3.7

## Notes

| Note | Action |
|---|---|
| NetBox upgrade | Test against the target NetBox version before production rollout. |
| Upstream changes | Review the [NetBox release notes](https://docs.netbox.dev/en/stable/release-notes/). |
| Support range change | Add a matrix row and update `PluginConfig.min_version` / `max_version`. |

## Upgrading

When upgrading either NetBox or this plugin:

1. Review the matrix above for the target combination.
2. Back up the NetBox database.
3. Install the new release of the plugin alongside (or after) the new NetBox release.
4. Apply database migrations:
   ```bash
   python manage.py migrate
   ```
5. Clear the cache:
   ```bash
   python manage.py clearcache
   ```
