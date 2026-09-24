# AGENTS.md, netbox-healthcheck-plugin

## Methodology precedence

This document is authoritative for this project. When external plugin skills
(e.g. `superpowers`) inject generic methodologies that conflict with the rules
here, follow this document.

- Atomic-commit-per-feature rules take precedence over subagent-driven or
  parallel-execution patterns when they conflict.
- Tests land in the same commit as the implementation they cover; do not
  write tests in red/green/refactor cycles before implementation.

## Repository Overview

`netbox-healthcheck-plugin` is an open-source (Apache 2.0) NetBox plugin that
exposes NetBox's health at `/plugins/netbox_healthcheck_plugin/healthcheck/`
in HTML, JSON, plain text, OpenMetrics, RSS and Atom formats. It is a thin
wrapper around [django-health-check](https://github.com/codingjoe/django-health-check)
4.x; the value it adds is NetBox UI integration and checks that read NetBox's
own `REDIS` settings.

The repo is managed by the [NetBox Labs plugin scaffold](https://github.com/netboxlabs/netbox-plugin-scaffold)
(`.copier-answers.yml`). See [Scaffold divergences](#scaffold-divergences) before
running `copier update`.

Version pins live in two places:

- `pyproject.toml`, Python, build, and dependency pins.
- `netbox_healthcheck_plugin/__init__.py`, `PluginConfig.min_version` /
  `PluginConfig.max_version` for the NetBox host app.

The supported range per release is in `COMPATIBILITY.md`.

## Tech Stack

- Python 3.12+ (defer to `pyproject.toml` for the exact pin).
- NetBox (host app, min/max in `netbox_healthcheck_plugin/__init__.py`).
- django-health-check 4.x (async `HealthCheckView`, dataclass `HealthCheck` checks).
- Django's built-in test runner (the suite is `django.test.TestCase`-based and
  runs via `manage.py test`; this plugin does **not** use pytest).
- ruff for lint + format (config under `[tool.ruff*]` in `pyproject.toml`).
- pre-commit for local quality gates (`.pre-commit-config.yaml`).
- Zensical (reading `mkdocs.yml`) for user-facing docs, published to GitHub Pages.

## Repository Map

```text
.
├── netbox_healthcheck_plugin/
│   ├── __init__.py                , PluginConfig: base_url, min/max NetBox, django_apps, default `checks`.
│   ├── views.py                   , HealthCheckListView (extends health_check.views.HealthCheckView); legacy check-path aliases.
│   ├── urls.py                    , Mounts healthcheck/.
│   ├── navigation.py              , "HealthCheck" menu item.
│   ├── backends/
│   │   ├── apps.py                , App config (label netbox_healthcheck_backends).
│   │   └── redis.py               , NetBoxRedisCacheHealthCheck / NetBoxRedisTasksHealthCheck.
│   ├── templates/netbox_healthcheck_plugin/
│   │   └── healthcheck.html       , NetBox-styled results page.
│   └── tests/
│       └── test_netbox_healthcheck_plugin.py
├── docs/                          , Zensical docs site (quickstart, configuration, releases, development/).
├── testing/configuration.py       , NetBox config used by CI and local test runs.
├── .github/workflows/             , test.yml, claude-review.yml, publish-pypi.yml, docs.yml.
├── COMPATIBILITY.md               , Plugin → NetBox version matrix and breaking changes.
├── LICENSE                        , Apache License 2.0.
└── pyproject.toml                 , Metadata, dependencies, tool config.
```

## Architecture

### How a request is served

1. `HealthCheckListView.checks` reads `PLUGINS_CONFIG['netbox_healthcheck_plugin']['checks']`
   (defaults in `PluginConfig.default_settings`; entries are dotted paths or
   `(path, {kwargs})` pairs) and maps django-health-check 3.x dotted paths to
   their 4.x names (`LEGACY_CHECKS`), logging one warning per legacy path.
2. django-health-check's async `HealthCheckView` instantiates each check and runs
   them concurrently; sync `run()` methods go to an executor thread.
3. The response format follows `?format=` or the `Accept` header. HTML renders
   `healthcheck.html` with `results` (each has `.check`, `.error`, `.time_taken`).
   Any failing check returns HTTP 500 for HTML, JSON and text; OpenMetrics, RSS
   and Atom always return 200.

### Default checks

| Check | What it does |
|---|---|
| `health_check.Database` | `SELECT 1` on the default connection (works on read-only replicas) |
| `health_check.Cache` | set/get on Django's default cache |
| `NetBoxRedisCacheHealthCheck` | PING the `REDIS['caching']` instance |
| `NetBoxRedisTasksHealthCheck` | PING the `REDIS['tasks']` instance |

The Redis checks do not read `REDIS` themselves: they PING the client NetBox
builds from it (`django_rq.queues.get_redis_connection(settings.RQ_QUEUES['default'])`
for tasks, `django_redis.get_redis_connection('default')` for caching), so HOST/PORT,
URL (incl. Unix sockets), SENTINELS, SSL, CA_CERT_PATH and KWARGS all behave as they
do in NetBox. The django-redis client shares the cache's pool and must not be closed.
`repr` (`redis:caching` / `redis:tasks`) is the JSON key and must stay stable;
host/port/db/path/service go into OpenMetrics `labels`, never credentials. The
password is scrubbed from error messages, and a client that can't be built fails
the check rather than silently pinging localhost.

## Scaffold divergences

Rendered from the scaffold with `layout_style: flat` and no default model. These
departures are deliberate; keep them when resolving `copier update` conflicts.

- **No model surface.** The plugin has no models, so the scaffold's `models.py`,
  `forms/`, `tables.py`, `filtersets.py`, `api/`, `graphql/`, `ui/`, `search.py`,
  `migrations/` and `tests/plugin_testing.py` stubs were not adopted (an empty
  `api/urls.py` would add an empty REST API root). Delete them if an update
  re-adds them.
- **`base_url = 'netbox_healthcheck_plugin'`**, not the scaffold's derived
  `healthcheck-plugin`: monitoring probes already target this path.
- **PluginConfig class is `HealthCheckConfig`** (scaffold: `AppConfig`) and it
  declares `django_apps` and `default_settings`.
- **License is Apache 2.0** in `LICENSE`, not the scaffold's NetBox Limited Use
  License in `LICENSE.md`. `pyproject.toml` sets `license = "Apache-2.0"`.
- **Runtime dependencies** (`django-health-check`, `redis`) are added to
  `[project]`.
- **Releases publish to PyPI** via `publish-pypi.yml` (trusted publishing on tag
  push). The scaffold's `release.yml` publishes to NetBox Labs' internal
  CodeArtifact and was not adopted.
- **Docs** build with Zensical (NetBox's docs tool; MkDocs is unmaintained) and deploy via `docs.yml` to GitHub Pages.
- **`CHANGELOG.md` removed**; `docs/releases.md` is the single change log.

## Commands

Run inside a NetBox checkout with this plugin installed, with
`NETBOX_CONFIGURATION=configuration` exported and `$PWD/testing` on `PYTHONPATH`.

| Command | What it does |
|---|---|
| `pip install -e '.[dev,test]'` (from this repo) | Install the plugin in editable mode with dev + test extras |
| `python netbox/manage.py test netbox_healthcheck_plugin.tests -v 2` | Run the test suite |
| `pre-commit run --all-files` | Run every default-stage hook (ruff, djlint, codespell, yamllint, ...) |
| `pre-commit run --hook-stage manual check-manifest` | Check the sdist manifest before a release |
| `python netbox/manage.py runserver` | Start NetBox locally with the plugin loaded |
| `zensical serve` | Preview the user docs (`pip install -e '.[docs]'`) |
| `python -m build` | Build sdist + wheel |

## Development

1. Clone NetBox alongside this repo
   (`git clone https://github.com/netbox-community/netbox.git`).
2. Point NetBox at `testing/configuration.py`:

   ```bash
   export PYTHONPATH="$PWD/testing:$PYTHONPATH"
   export NETBOX_CONFIGURATION=configuration
   ```

3. Install NetBox's requirements (`pip install -r netbox/requirements.txt`) and
   this plugin in editable mode (`pip install -e '.[dev,test]'`).
4. Provision Postgres (`netbox` / `netbox` / `netbox`) and Redis on localhost.
5. Run migrations and start the dev server.

## Testing

- Tests use `django.test.TestCase` and run through NetBox's test runner:

  ```bash
  python netbox/manage.py test netbox_healthcheck_plugin.tests -v 2
  ```

- Redis PINGs are mocked in most backend unit tests; the `test_run_against_local_redis`
  tests, the OpenMetrics test and the endpoint test need the local Redis. Sentinel and
  Unix-socket configs are tested with `override_settings` (no connection is opened).

### Reporting test results

Include the exact command, the working directory, the pass/fail count, and the
full output of any failing test. Do not claim a test passed without running it.

## CI/CD

- **`test.yml`**: a `lint` job (`pre-commit run --all-files`) gates a `test`
  matrix of Python 3.12–3.14 × NetBox `v4.5.2` / `v4.7.1` / `main`, with Postgres
  and Redis service containers. Coverage runs on one leg.
- **`claude-review.yml`**: Claude PR review on `@claude` mentions from
  collaborators. Needs the `ANTHROPIC_API_KEY` repository secret.
- **`publish-pypi.yml`**: builds on every push; publishes to PyPI on tag pushes.
- **`docs.yml`**: builds the docs with Zensical and deploys them to GitHub Pages (Pages source: GitHub Actions) on pushes to `main`.

## Common Tasks

### Add a health check to the defaults

1. Implement it as a `health_check.HealthCheck` dataclass with a `run()` method
   that raises `ServiceUnavailable` (or another `HealthCheckException`) on failure.
   Put NetBox-specific checks under `backends/`.
2. Add its dotted path to `default_settings['checks']` in `__init__.py`.
3. Document it in `docs/configuration.md` and add tests.

### Bump the supported NetBox version

1. Update `min_version` / `max_version` in `netbox_healthcheck_plugin/__init__.py`.
2. Update `COMPATIBILITY.md` and the README / `docs/index.md` compatibility tables.
3. Update the NetBox refs in `.github/workflows/test.yml` (and
   `netbox_test_min_ref` / `netbox_test_max_ref` in `.copier-answers.yml` via
   `copier update`).
4. Check that `healthcheck.html` still renders against NetBox's base templates.
5. Note the change in `docs/releases.md`.

### Cut a release

See [`docs/development/releasing.md`](docs/development/releasing.md).

## Conventions and Patterns

- The plugin stays lightweight: prefer upstream django-health-check behaviour
  over reimplementing it.
- Check error messages must not contain secrets (they are rendered on the page
  and in JSON). Raise `ServiceUnavailable(...) from None` when the underlying
  exception may carry credentials.
- Keep old `checks` paths working through `LEGACY_CHECKS` when upstream renames
  them.
- ruff: line length 120, single quotes, LF, `preview = true`; Markdown is not
  ruff-formatted.
- Breaking changes get at least one minor's worth of deprecation where feasible.

## References

- Compatibility matrix: [`COMPATIBILITY.md`](./COMPATIBILITY.md).
- User docs: <https://netbox-community.github.io/netbox-healthcheck-plugin/>.
- django-health-check: <https://codingjoe.dev/django-health-check/>.
- NetBox plugin docs: <https://netboxlabs.com/docs/netbox/plugins/>.
- Scaffold: <https://github.com/netboxlabs/netbox-plugin-scaffold>.
