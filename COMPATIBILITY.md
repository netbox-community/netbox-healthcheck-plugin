# Compatibility Matrix

This document tracks the compatibility between NetBox HealthCheck Plugin releases and NetBox versions.

## Version Compatibility

| Release | Minimum NetBox Version | Maximum NetBox Version | Python Version       |
|---------|------------------------|------------------------|----------------------|
| 0.3.0   | 4.5.0                  | 4.99.99                | 3.12, 3.13, 3.14     |
| 0.2.0   | 4.0.0                  | 4.4.x                  | 3.10, 3.11, 3.12     |
| 0.1.4   | 3.4.0                  | 3.7.x                  | 3.10, 3.11, 3.12     |
| 0.1.3   | 3.4.0                  | 3.7.x                  | 3.10, 3.11, 3.12     |
| 0.1.2   | 3.4.0                  | 3.7.x                  | 3.10, 3.11, 3.12     |
| 0.1.0   | 3.4.0                  | 3.7.x                  | 3.10, 3.11, 3.12     |

## Breaking Changes

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

- The plugin follows semantic versioning
- Each minor version (0.x.0) may introduce breaking changes
- Patch versions (0.x.y) are backwards compatible within the same minor version
- Always review the CHANGELOG.md before upgrading

## Testing

Each release is tested against:
- Multiple Python versions (as shown in the table above)
- Target NetBox versions specified in the compatibility range
- Redis 7.x and PostgreSQL 12+

For the most up-to-date compatibility information, see the [README.md](README.md) file.
