# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

We love your input! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## General Tips for Working on GitHub

* Register for a free [GitHub account](https://github.com/signup) if you haven't already.
* You can use [GitHub Markdown](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax) for formatting text and adding images.
* To help mitigate notification spam, please avoid "bumping" issues with no activity. (To vote an issue up or down, use a :thumbsup: or :thumbsdown: reaction.)
* Please avoid pinging members with `@` unless they've previously expressed interest or involvement with that particular issue.
* Familiarize yourself with [this list of discussion anti-patterns](https://github.com/bradfitz/issue-tracker-behaviors) and make every effort to avoid them.

## Types of Contributions

### Report Bugs

Report bugs at [GitHub Issues](https://github.com/netbox-community/netbox-healthcheck-plugin/issues).

If you are reporting a bug, please include:

* Your operating system name and version
* Your NetBox version
* Your Python version
* Any details about your local setup that might be helpful in troubleshooting
* Detailed steps to reproduce the bug

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help wanted" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement" and "help wanted" is open to whoever wants to implement it.

### Write Documentation

NetBox HealthCheck Plugin could always use more documentation, whether as part of the official docs, in docstrings, or even on the web in blog posts and articles.

### Submit Feedback

The best way to send feedback is to file an issue at [GitHub Issues](https://github.com/netbox-community/netbox-healthcheck-plugin/issues).

If you are proposing a feature:

* Explain in detail how it would work
* Keep the scope as narrow as possible, to make it easier to implement
* Remember that this is a volunteer-driven project, and that contributions are welcome!

## Development Setup

Ready to contribute? Here's how to set up the plugin for local development:

### 1. Fork and Clone

Fork the repository on GitHub and clone your fork locally:

```bash
git clone git@github.com:your_username/netbox-healthcheck-plugin.git
cd netbox-healthcheck-plugin
```

### 2. Set Up NetBox Development Environment

Follow the [NetBox Development Environment Guide](https://docs.netbox.dev/en/stable/development/getting-started/) to set up NetBox for plugin development.

Activate the NetBox virtual environment:

```bash
source ~/.venv/netbox/bin/activate
```

### 3. Install Plugin in Development Mode

Install the plugin in editable mode with development dependencies:

```bash
pip install -e ".[test,docs]"
```

This creates symbolic links within your Python environment to the plugin development directory.

### 4. Install Pre-commit Hooks

Install pre-commit hooks to automatically check code quality:

```bash
pre-commit install
```

### 5. Create a Feature Branch

Create a branch for your changes:

```bash
git checkout -b name-of-your-bugfix-or-feature
```

Now you can make your changes locally.

## Development Workflow

### Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for linting issues
ruff check .

# Automatically fix issues
ruff check --fix .

# Format code
ruff format .
```

Pre-commit hooks will automatically run these checks before each commit.

### Running Tests

Run the test suite using pytest:

```bash
pytest
```

Or using NetBox's test runner:

```bash
cd /path/to/netbox
python manage.py test netbox_healthcheck_plugin
```

### Building Documentation

Build and preview documentation locally:

```bash
mkdocs serve
```

Then open http://127.0.0.1:8000 in your browser.

### Testing with NetBox

To test the plugin with a running NetBox instance:

1. Ensure the plugin is installed in development mode (step 3 above)
2. Add the plugin to NetBox's `configuration.py`:

```python
PLUGINS = ['netbox_healthcheck_plugin']
PLUGINS_CONFIG = {
    "netbox_healthcheck_plugin": {}
}
```

3. Restart NetBox
4. Visit the health check endpoint: `/plugins/netbox_healthcheck_plugin/healthcheck/`

## Pull Request Guidelines

Before submitting a pull request:

1. **Include tests** - The PR should include tests for new functionality
2. **Update documentation** - Update docs for new features or changed behavior
3. **Follow code style** - Ensure Ruff checks pass
4. **Update CHANGELOG.md** - Add an entry describing your changes
5. **Test across Python versions** - The PR should work for Python 3.12, 3.13, and 3.14

Check the [GitHub Actions](https://github.com/netbox-community/netbox-healthcheck-plugin/actions) status to ensure all checks pass.

## Commit Messages

Write clear, descriptive commit messages:

* Use present tense ("Add feature" not "Added feature")
* Use imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

## Submitting Changes

1. Commit your changes:

```bash
git add .
git commit -m "Your detailed description of changes"
```

2. Push to your fork:

```bash
git push origin name-of-your-bugfix-or-feature
```

3. Submit a pull request through GitHub

## Release Process

For maintainers:

1. Ensure all changes are committed and tests pass
2. Update version in `pyproject.toml` and `netbox_healthcheck_plugin/__init__.py`
3. Update `CHANGELOG.md` with release notes
4. Create a new release on GitHub with a version tag (e.g., `v0.3.0`)
5. GitHub Actions will automatically publish to PyPI

## Questions?

If you have questions or need help, please:

* Open a [Discussion](https://github.com/netbox-community/netbox-healthcheck-plugin/discussions)
* Ask in the [NetBox Slack community](https://netdev.chat/)
* Check the [NetBox plugin documentation](https://docs.netbox.dev/en/stable/plugins/)

Thank you for contributing!
