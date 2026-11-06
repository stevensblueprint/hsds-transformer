# BLU-12 local verification — 2026-11-03

This is repository/tooling evidence, **not a known-good deployment record**.
The [release checkpoint](baseline-release.md) remains open.

- Final base: `c4669486e582a4b46a73f72e9982498f83898875` (main rechecked before push).
- Candidate: the BLU-12 PR commit containing this record. Application, dependency,
  Dockerfile and workflow files are unchanged from that base.
- Tested smoke script SHA-256:
  `3623d01b9b01040d866ce8312f0e176766820fdfccfa23dad7fb2b1010b132b9`.
- Environment: Linux, Python 3.13.5, uid/gid 1000, uv 0.11.21,
  locked API/dev dependencies, Docker server 28.4.0.
- Checkout: `/workspace/blu-12`, isolated worktree on
  `codex/blu-12-baseline-evidence`; no changes to another contributor's branch.
- The preinstalled uv was 0.12.23. Installed 0.11.21 in `/tmp/blu12-tools`
  and used `UV_CACHE_DIR=/tmp/blu12-uv-cache` because the default home cache is
  read-only. Commands below use that executable/cache in place of `uv`.

| Check / command from repository root | Status | Observation / limitation |
| --- | --- | --- |
| `uv sync --locked --extra api` | PASS | Locked environment installed, no lock changes. |
| `uv run --locked --extra api python -m pytest tests/ -q` | PASS | 224 passed in 1.16s; one existing Starlette TestClient/httpx deprecation warning. Includes API contracts, temp-root unit tests and request isolation/cleanup tests. |
| `uv run --locked --extra api ruff check .` | PASS | All checks passed, including the new smoke script. |
| `git diff --check` and relative Markdown file-target check | PASS | No whitespace errors or missing local document targets. |
| `HSDS_TMP_DIR=/tmp/blu12-api-temp .venv/bin/python -m uvicorn src.api.app:app --host 127.0.0.1 --port 18012` then `.venv/bin/python scripts/baseline_smoke.py --base-url http://127.0.0.1:18012` | PASS | Real local HTTP at 15:59:11 UTC; output retained below. No TestClient transport in this smoke. |
| Same smoke with `--base-url http://127.0.0.1:18012/missing` | PASS | Expected negative control: exit 1 with `RuntimeError: Health returned 404`; does not mistake a missing API for success. |
| Run the documented temp probe with the local API's interpreter, user and `HSDS_TMP_DIR` | PASS | uid/gid 1000, root `/tmp/blu12-api-temp`; create/read/delete passed; root empty after completed smoke requests. This is host-user evidence, not container permissions. |
| `DOCKER_CONFIG=/tmp/blu12-docker docker build -t hsds-blu12:local .` | FAIL | Attempted before rebase on `efff022`; unchanged Dockerfile/lock. Dockerfile line 13 dependency download failed: `boltons==25.0.0`, DNS lookup failure after retries. No image was produced. Initial build attempt also hit read-only default buildx directory; redirected Docker config to writable `/tmp`. |
| Container smoke, running registry digest, baseline environment permissions, rollback rehearsal | NOT RUN | Local image build unavailable; agreed environment, owner, access, previous known-good digest/config and authorization for deployment/rehearsal are unresolved. |

Successful local smoke output (exit 0):

```text
Started 2026-11-03T15:59:11.590289+00:00
PASS health
PASS csv ZIP content
PASS json ZIP content
PASS JSON multipart content
PASS invalid ZIP rejection
PASS health after rejection
PASS smoke only; image identity, runtime permissions and rollback require separate evidence
```

The helper reuses the fixture expectations from `tests/test_api_transform.py`.
No API behavior was changed. The malformed ZIP smoke covers one failure mode;
unit tests do not substitute for runtime permission or rollback evidence. No
capacity test, production migration, deployment, image publication, merge, or
release was performed. Local API process was stopped after verification.

Read-only Linear field-note lookup returned `Tool get_agent_context not found`;
the issue and repository were inspected directly. Initially PR #158 was the
only returned open transformer PR. Main changed during verification: #158 merged
as `c466948`. Rebased onto it and reran the full suite, Ruff, and live smoke; the
final results above supersede the initial 198-test run on `efff022`. The negative
control and host permission probe ran before rebase with the unchanged helper
and tempdir code; the temp root was again empty after the final smoke. Concurrent BLU-11 work may add setup docs:
keep setup instructions authoritative in the README and link this checkpoint
from the final runbook rather than treating another agent's branch as merged.
