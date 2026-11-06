# Contributor runbook

This is the canonical forward-path setup and verification sequence. Run commands
from the repository root in Bash on Linux/macOS. The recorded execution below is
Linux with Python 3.13. Windows PowerShell setup and health commands are included
below; related Windows contributor results and their limits are recorded at the
end. The complete sequence has not been independently checked on Windows or macOS.
This is contributor evidence, not a known-good release or deployment procedure.

## Install and check

Prerequisites: Git, Python 3.13, uv **0.11.21**, curl, and (for the final section)
Docker Engine with Compose v2. Install the pinned uv with
`python3 -m pip install uv==0.11.21` in an environment you can write to, then
check `uv --version`. A different uv version is rejected by `pyproject.toml`.

```bash
git clone https://github.com/stevensblueprint/hsds-transformer.git
cd hsds-transformer
git rev-parse HEAD
uv --version
uv sync --locked --extra api --python 3.13
uv run --locked --extra api python --version
uv run --locked --extra api ruff check .
uv run --locked --extra api python -m pytest tests/ -v
```

Expected: Python 3.13.x, Ruff reports `All checks passed!`, and pytest succeeds.
The baseline recorded below has 224 tests and one Starlette TestClient/httpx
deprecation warning. Test counts can change with subsequent commits.

`api` is an optional extra; pytest, httpx and Ruff belong to the default `dev`
dependency group, **not** a `dev` extra. Plain sync does not install the API.
`uv.lock` is authoritative; do not remove `--locked` to work around a lock error.
See [dependency setup](../README.md#dependency-setup) for core-only/API-only
variants and the generated pip export. These are alternatives, not extra steps
in the contributor sequence.

### Windows uv and PATH

In PowerShell, install the pinned uv with the Python interpreter you intend to
use. If pip reports that its Scripts directory is not on PATH, add the directory
it names to PATH and open a new terminal, or use `python -m uv` instead of `uv`.
For a user install on Python 3.13, that directory may be
`%APPDATA%\Python\Python313\Scripts`; use pip's actual path, not that example
blindly. The module fallback must use the same `python` that installed uv.

From the repository root:

```powershell
python -m pip install uv==0.11.21
python -m uv --version
python -m uv sync --locked --extra api --python 3.13
python -m uv run --locked --extra api python --version
```

Expected: uv 0.11.21 and project Python 3.13.x. This fallback also applies to the
locked Ruff, pytest, and API commands. The Bash variables and heredocs in later
sections are not PowerShell syntax. See the Windows results below for two known
platform-specific pytest failures; successful setup does not imply the full
Windows suite passes.

## CSV and JSON CLI

Use a new output directory each time so old files cannot make a failed run appear
successful. Keep the temporary path printed below for inspection and cleanup.

```bash
RUNBOOK_TMP=$(mktemp -d)
export RUNBOOK_TMP
printf '%s\n' "$RUNBOOK_TMP"
uv run --locked --extra api python -m src.cli.main data/sanity_check -o "$RUNBOOK_TMP/csv"
uv run --locked --extra api python -m src.cli.main data/json_test -f json -o "$RUNBOOK_TMP/json"
uv run --locked --extra api python - <<'PY'
import json
import os
from pathlib import Path
root = Path(os.environ['RUNBOOK_TMP'])
for kind in ('csv', 'json'):
    paths = list((root / kind).glob('*.json'))
    assert [p.name for p in paths] == ['organization_1.json'], paths
    obj = json.loads(paths[0].read_text())
    assert obj['id'] == '1' and obj['name'] == 'Test Organization'
    assert obj['description'] == 'Clean Me'
    if kind == 'csv':
        assert {s['id'] for s in obj['services']} == {'101', '102'}
    print(kind, 'OK:', paths[0].name)
PY
```

Expected: each CLI exits zero; assertions print `csv OK: organization_1.json`
and `json OK: organization_1.json`. CSV nests services under the organization;
JSON exercises the separate JSON mapping path. These fixture assertions do not
certify arbitrary inputs as HSDS schema-valid.

Without `-o`, output goes to `output/` relative to the working directory. Files
are named `<object_type>_<id>.json`. Existing matching files are overwritten and
unrelated old files remain; writes are not atomic. Missing/duplicate output
identities fail preflight. Repeated entity-type source groups can still be lost
upstream (BLU-16), and output accounting/atomicity remain BLU-23 work.

## Local API

In a second terminal, from the same checkout:

```bash
mkdir -p /tmp/hsds-runbook-api
HSDS_TMP_DIR=/tmp/hsds-runbook-api uv run --locked --extra api python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Use `src.api.app:app`. The historical `api.app:app --app-dir src` command fails
with package-relative imports. Stop the server with Ctrl-C when finished.

### Windows local API and health

In PowerShell, from the same checkout, start the API with the uv module fallback:

```powershell
python -m uv run --locked --extra api python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

In a second PowerShell terminal, use `curl.exe` explicitly so Windows PowerShell
cannot substitute its `curl` alias:

```powershell
curl.exe --fail --silent --show-error http://127.0.0.1:8000/health
```

Wait for Uvicorn's `Application startup complete` message before checking health.
Expect HTTP 200 and JSON with `"status":"ok"`; timestamp and uptime vary. Stop the
server with Ctrl-C. Without `HSDS_TMP_DIR`, this command uses the API's default
writable temporary directory selection described below.

### API workspace and transformation checks

`HSDS_TMP_DIR` controls the API transformation workspace and response ZIP temp
files. It is checked for writability and created if possible; an explicitly
configured unwritable path fails rather than falling back. Without it, the API
tries system temp locations. The configured path must be writable by the runtime
user. This setting does not configure every multipart parser spool or OS temp
consumer. Request workspaces and response ZIPs are cleaned after normal responses;
interruption behavior is covered by the full suite.

Back in the first terminal (which retains `RUNBOOK_TMP`), run:

```bash
curl --fail --silent --show-error http://127.0.0.1:8000/health
curl --fail --silent --show-error -D "$RUNBOOK_TMP/api.headers" \
  -F 'zip_file=@data/sal_example.zip' \
  http://127.0.0.1:8000/transform -o "$RUNBOOK_TMP/api.zip"
uv run --locked --extra api python - <<'PY'
import json
import os
from pathlib import Path
from zipfile import ZipFile
root = Path(os.environ['RUNBOOK_TMP'])
headers = (root / 'api.headers').read_text().lower()
assert '201 created' in headers, headers
assert 'content-type: application/zip' in headers, headers
assert 'attachment; filename=transformed.zip' in headers, headers
with ZipFile(root / 'api.zip') as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    assert len(names) == 10, names
    for name in names:
        obj = json.loads(archive.read(name))
        assert name == f"organization_{obj['id']}.json"
        assert obj['name']
print('API OK: 201, ZIP, 10 organizations')
PY
```

Health returns HTTP 200 with `status: "ok"`; timestamp and uptime vary. Transform
returns HTTP 201 and the assertions print `API OK: 201, ZIP, 10 organizations`.
JSON ZIP uploads use the same endpoint with `-F input_format=json` and matching
JSON source/mapping files. `POST /transform/stream` takes repeated `files` parts
with source and mapping JSON. Both formats and the streaming response are checked
by `tests/test_api_transform.py` in the full suite.

On the baseline below, ZIP uploads have a 5 MiB compressed limit, 1,000 members,
20 MiB per expanded file, 50 MiB total expanded bytes, and a 100:1 per-member
expansion ratio. See the [ZIP contract](../README.md#running-the-api) for supported
archives and 413/422 responses. Streamed JSON staging has a 50 MiB aggregate
file-content limit. These are provisional defaults, not end-to-end memory or
CPU bounds. PR #158 merged during this work and is included in the final baseline.
Custom Python transforms are CLI-only, execute trusted local code, and must be
supplied with `--transforms` when mappings declare them. The API rejects unavailable
custom transforms; it does not execute uploaded Python.

## Compose

Stop the local API first to free port 8000. Compose uses the fixed container name
`hsds-transformer-api`; do not start it over another contributor's container.
Use the same checkout and first terminal so `RUNBOOK_TMP` remains set.
`docker compose up -d` returns before Uvicorn is necessarily ready. Allow startup
time before checking health. If an early check returns `Empty reply from server`
or a connection reset, inspect `docker compose logs api`, wait for
`Application startup complete`, and retry the health check. Persistent errors
are failures to investigate, not a successful startup.

```bash
docker compose config --quiet
docker compose up --build -d
curl --fail --retry 15 --retry-connrefused --retry-delay 2 http://127.0.0.1:8000/health
```

For a Windows PowerShell health check after Compose starts, use
`curl.exe --fail --silent --show-error http://127.0.0.1:8000/health`. The same
startup wait applies; a running container alone does not prove the API is ready.

Then repeat the API curl and ZIP assertion block above against the container
using the Bash terminal required by that block.
Expected results are the same (200 health; 201 ZIP with 10 organizations).
For diagnostics and teardown:

```bash
docker compose ps
docker compose logs api
docker compose down
```

Always tear down your own Compose stack after the check, including on failure.
Retain output artifacts for review, then remove only the temporary directories
you created. A successful build alone is not a successful API smoke check.

The [Dockerfile](../Dockerfile) uses `python:3.13-slim`, copies pinned uv 0.11.21,
copies `pyproject.toml` and `uv.lock` for a cached
`uv sync --locked --no-default-groups --extra api --no-install-project`, then
copies the repository **once** with nonroot ownership. It runs as `nonroot` with
`APP_MODULE=src.api.app:app`; Compose does not override that module. The image
runs source from `/app` rather than installing the project wheel. Base-image tags
are mutable; locked Python dependencies alone do not identify a reproducible
image digest. No image push is part of this runbook.

## Verification record and remaining acceptance

Verified 2026-11-03 in a new remote clone at main
`efff0223a914f2d011e511f29670d93b41801f0c`, then updated to merged main
`c4669486e582a4b46a73f72e9982498f83898875` and reran sync, lint, all tests,
CLI/API assertions, and Compose configuration with this documentation patch.
The local Docker build failure below was observed on the initial baseline; no
local container runtime result is claimed for either revision. Hosted Compose
smoke passed on [the initial candidate](https://github.com/stevensblueprint/hsds-transformer/actions/runs/41669632246)
(`710b9f22ecc595e1d7f80e0f96362e54098ca1ce`) and on [the later candidate](https://github.com/stevensblueprint/hsds-transformer/actions/runs/41711734868)
(`4e6748c3752e62146209dd9e8ba701cc1e5e3da6`). Both built and started the
container, checked health, transformed the sample ZIP, checked ZIP integrity,
and tore down the stack. These runs did not perform the complete runbook
assertions or the independent teammate walkthrough.
Environment: Linux, CPython 3.13.5, uv 0.11.21, Docker 28.4.0, Compose v2.40.3.
The sandbox's default Python was 3.12 and uv was 0.12.23, so checks used
`uvx uv==0.11.21` in place of `uv` with writable `UV_CACHE_DIR`, `UV_TOOL_DIR`,
and `UV_PYTHON_INSTALL_DIR` under `/tmp`; `--python 3.13` selected `/usr/bin/python3.13`.
The project `.venv` was created from scratch. Compose config/build used
`docker compose -p blu11 config --quiet` and `DOCKER_CONFIG=/tmp/blu11-docker docker compose -p blu11 build`;
the writable Docker config avoided the sandbox's read-only home directory. This is not an independent teammate
walkthrough or evidence for a released image.

| Check | Result |
| --- | --- |
| Locked sync with API/default dev dependencies | PASS |
| Full pytest suite | PASS: 224 tests; one TestClient deprecation warning |
| Locked Ruff | PASS |
| CSV/JSON commands and content assertions above | PASS |
| Corrected Uvicorn startup, live health/CSV API, ZIP contents | PASS |
| Historical `api.app` import with `src` on path | FAIL as expected: relative import beyond top-level package |
| Compose configuration | PASS |
| Compose image build | FAIL: container DNS could not resolve `files.pythonhosted.org` while downloading urllib3 2.8.0 |
| Local Compose runtime health/transform | NOT RUN: blocked by the local image build failure |
| Hosted Compose runtime smoke | PASS on both candidates linked above; sample ZIP integrity checked |
| Independent teammate fresh-checkout walkthrough | NOT RUN; still required for BLU-11 acceptance |
| Windows/macOS; reverse round-trip/pilot behavior | NOT RUN; outside this verified path |

Dependency PR #151, package PR #157, test-guidance PR #150, and Compose PR #147
are already in this baseline. No additional Docker-copy change is needed.
BLU-29 owns quick-start verification; this record supplies the broader forward
runbook without declaring that issue or BLU-11 accepted. Reverse transformation
is partial and non-gating unless a pilot explicitly requires it. A teammate must
repeat this sequence from a new clone, record exact SHA/tool versions/results
(including Compose), and resolve any failures before closing the broader issue.

### Related Windows contributor evidence

[Bradley's BLU-29 PR #165](https://github.com/stevensblueprint/hsds-transformer/pull/165)
reports Windows 11, Python 3.13.2, and uv 0.11.21 verification. Its fresh-clone
setup, API health, and Compose transform passed at `090c879`; the PR also reports
a teammate README follow-through at `43c63dd`. After merging main, at `d82d33a`,
locked sync, Ruff, and local API health passed, but pytest had 222 passes and two
failures in `tests/test_api_zip_limits.py` (backslash path validation and an
overlong member path). Compose was not rerun at that revision.

These are contributor-reported results on the named revisions, not a fresh
Windows run of this canonical runbook or a clean final-head test result. This
runbook preserves the uv/PATH and health guidance from #165 without duplicating
its setup sequence across the contributor guides. The Windows failures and a
complete independent runbook walkthrough remain follow-up work before claiming
full Windows or BLU-11 acceptance.
