# HSDS repository check sources

Use the current [AGENTS Testing Guidelines](../../../../AGENTS.md#testing-guidelines)
for environment setup, CI-aligned commands, and evidence reporting. That section
incorporates merged [PR #150](https://github.com/stevensblueprint/hsds-transformer/pull/150);
do not maintain a second copy of its command list here.

Validate commands against [pyproject.toml](../../../../pyproject.toml),
[requirements.txt](../../../../requirements.txt), and the
[Ruff](../../../../.github/workflows/ruff.yml),
[unit-test](../../../../.github/workflows/unit-tests.yml), and
[Docker smoke](../../../../.github/workflows/docker-smoke.yml) workflows.
Use [endpoint regression tests](../../../../tests/test_api_transform.py) and the
[README endpoint recipe](../../../../README.md#endpoint-regression-tests) for API changes.
The README also contains legacy CLI checks; those do not replace the pytest suite.

The backend uses Python; this checkout does not contain the separate
`stevensblueprint/hsds-transformer-ui` application. Inspect that repository's current
manifest before suggesting UI commands. No frontend tooling is required by these skills.
A passing Docker archive check alone does not verify transformed JSON contents.
