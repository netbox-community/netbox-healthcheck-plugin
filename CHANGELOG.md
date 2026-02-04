# Changelog

## 0.3.0

* Replace `health_check.contrib.redis` with custom NetBox Redis health check backends
* Add health checks for both Redis instances: `caching` and `tasks`
* BREAKING: Redis health checks now read directly from NetBox's `REDIS` configuration dict, rather than requiring a separate `REDIS_URL` Django setting

## 0.2.0 (2024-05006)

* Updates for NetBox v4.0

## 0.1.2 (2024-04-08)

* Fix django-health-check dependency in pyproject.toml

## 0.1.2 (2024-04-05)

* General cleanup

## 0.1.0 (2023-01-18)

* First release on PyPI.

