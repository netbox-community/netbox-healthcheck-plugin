# Releasing

We follow [Semantic Versioning](https://semver.org/) and keep a Change Log in `docs/releases.md`.

## Checklist

1. **Finish code and docs.** Confirm CI is green on the default branch, all
   relevant documentation updates have landed, and `docs/releases.md`
   reflects the changes in this release.

2. **Change log.** Add a new `## vX.Y.Z` section at the top of
   `docs/releases.md`, above the previous release and separated from it by a
   `---` rule. Group entries under `### Enhancements` and `### Bug Fixes`
   subsections, each bullet `* [#<issue>](<url>) - <summary>`. The very first
   release is a bare `* Initial release` with no subsections.

3. **Version bump.** Update `version = "X.Y.Z"` in `pyproject.toml` and
   `__version__` in `netbox_healthcheck_plugin/__init__.py`, and add the
   release to `COMPATIBILITY.md` and the README compatibility table.
   Commit with a message of the form `chore: release X.Y.Z`.

4. **Tag.** Create an annotated tag matching the version and push it
   together with the release commit:

   ```bash
   git tag -a vX.Y.Z -m "Release X.Y.Z"
   git push origin main vX.Y.Z
   ```

5. **CI.** Pushing the tag fires `.github/workflows/publish-pypi.yml`,
   which builds the wheel and sdist and publishes them to
   [PyPI](https://pypi.org/p/netbox-healthcheck-plugin) using trusted
   publishing (the `pypi` environment). Watch the run for failures.

6. **Publish release.** GitHub drafts a release from the new tag. Review
   the auto-generated notes against `docs/releases.md`, edit as needed,
   and publish.

7. **Post-release.** Verify the new version is on PyPI and that a fresh
   `pip install netbox-healthcheck-plugin` resolves it.

## Hotfix process

For an urgent fix on a published version, branch from the release tag,
apply the fix, and follow the same checklist with the patched version
number:

```bash
git switch -c hotfix/X.Y.(Z+1) vX.Y.Z
# ...apply fix, update changelog, bump version...
git tag -a vX.Y.(Z+1) -m "Release X.Y.(Z+1)"
git push origin hotfix/X.Y.(Z+1) vX.Y.(Z+1)
```

Merge the hotfix branch back into the default branch after the release
goes out.

## See also

- [Contributing](contributing.md) for the pre-release development flow.
