# Baseline release and rollback checkpoint (BLU-12)

**Status: NOT CERTIFIED.** No agreed deployed baseline, running image digest,
environment owner, or completed rollback rehearsal has been established by this
record. Local tests and image publication are insufficient to close
[BLU-12](https://linear.app/stevensblueprint/issue/BLU-12/record-a-known-good-baseline-release-and-rollback-procedure).
Keep the Phase 0 exit checkpoint open until the release owner completes the record
below. This document grants no deployment or publication permission.

## Observed repository state

Inspected main: `c4669486e582a4b46a73f72e9982498f83898875` on 2026-11-03.

- [ECR workflow](../.github/workflows/deploy.yml) builds and pushes timestamp/short-SHA
  tags and `latest`; it does not update or inspect a running service.
- [GHCR workflow](../.github/workflows/build.yml) smokes a locally built Compose
  container, then separately builds and publishes SHA and `latest` tags. This does
  not establish which digest is running in the baseline environment.
- [Compose](../docker-compose.yml) builds from the checkout; `up --build` is not an
  immutable-image rollback. Its fixed container name can collide with other work.
- [Dockerfile](../Dockerfile) uses `nonroot`, `PORT=8000`, and
  `APP_MODULE=src.api.app:app`. Base image tags are mutable, so rebuilding the same
  source commit does not prove the same image bytes.
- `/health` is liveness, not release identity: its version is the API version,
  not a Git SHA or registry digest. Read running-image identity from the platform.
- BLU-10 cleanup is included through merged PR #161. [BLU-6 PR #158](https://github.com/stevensblueprint/hsds-transformer/pull/158)
  merged during this work as `c4669486e582a4b46a73f72e9982498f83898875`; the
  final verification includes bounded ZIP extraction. Recheck dependencies BLU-5 through BLU-11
  and any concurrent setup/runbook changes before selecting a release candidate.

## Owner's immutable release record

Copy this section into a dated evidence record for each candidate and each
previous known-good target. Preserve failed attempts. Use UTC timestamps and
durable links accessible to the team; omit tokens, credentials, and uploaded user
data. Record secret references/version IDs, never secret values.

| Required field | Value / evidence |
| --- | --- |
| Status | NOT CERTIFIED / candidate / known-good (only after all gates pass) |
| Environment and exact service/resource ID | UNRESOLVED; do not infer from CORS origins or registry names |
| Release owner, verifier, approval and approved deployment procedure | UNRESOLVED |
| Full source commit and dependency PR state | UNRESOLVED |
| Registry image reference `repository@sha256:…` | UNRESOLVED; a tag alone is insufficient |
| Build run and provenance connecting commit to digest | UNRESOLVED |
| Platform / architecture and resolved platform image digest | UNRESOLVED; distinguish a multi-platform index from its selected image |
| Running revision/task/container IDs and observed digests | UNRESOLVED; verify all serving replicas, not only the desired configuration |
| Configuration revision | UNRESOLVED; command, PORT, APP_MODULE, HSDS_TMP_DIR, runtime UID/GID, mounts/permissions, resource limits, networking/ingress and secret references |
| Health URL, test timestamp and smoke output | UNRESOLVED |
| Temporary-root write/delete and cleanup evidence as runtime user | UNRESOLVED |
| Previous known-good digest, configuration and evidence link | UNRESOLVED; cannot rehearse a verified rollback without a verified target |
| Rollback rehearsal approval, operator, start/end times and result | UNRESOLVED |
| Project checkpoint link and owner sign-off | UNRESOLVED |

Confirm both images remain pullable by the environment before a change. Retain
the previous image and its configuration through the agreed rollback window;
record that window and any registry retention exception with the owner. Stop if
the digest/source relationship, rollback target, or required access is missing.

## Capture the running service checks

Use the locked development environment from [the setup guide](../README.md#dependency-setup)
on the test client. The following command sends small checked-in sample data and
one deliberately invalid ZIP to the explicitly selected API. Run it only against
the agreed environment. It follows no redirects and fails nonzero on an unmet
expectation. Include any ingress path prefix in the URL. Authenticated environments
need an approved access path; do not put credentials in a URL or evidence log.

```bash
# From the repository root; set this to the approved environment's API URL.
export BASELINE_URL='http://127.0.0.1:8000'
uv run --locked --extra api python scripts/baseline_smoke.py \
  --base-url "$BASELINE_URL" > baseline-smoke.txt 2>&1
# Check the exit code immediately; retain output even on failure.
```

The smoke checks 200 health with `status=ok` and `Cache-Control: no-store`, then
201 ZIP responses, attachment headers, archive integrity, and organization ID/name
for CSV ZIP (`data/iCarol`) and JSON ZIP/multipart (`data/json_test`). It requires
422 `Invalid zip file` with no attachment for malformed input, then healthy
recovery. It does not validate every HSDS field, load/capacity, authentication,
browser behavior, interrupted connections, or all hostile archive cases.

Check temporary permissions **inside the selected runtime using its configured
application user**, not root on the host. For a Docker runtime the following is
a diagnostic example, not an assumed deployment architecture; set the verified
container ID first. On another platform, use its approved exec equivalent.

```bash
docker exec "$BASELINE_CONTAINER" python -c '
import os, pathlib, tempfile
from src.api.tempdir import get_writable_temp_dir
root = get_writable_temp_dir()
print("uid", os.getuid(), "gid", os.getgid(), "temp_root", root)
with tempfile.TemporaryDirectory(dir=root, prefix="baseline-permission-") as name:
    path = pathlib.Path(name) / "probe"
    path.write_text("probe")
    assert path.read_text() == "probe"
    path.unlink()
assert not pathlib.Path(name).exists()
print("PASS create/read/delete")
'
```

Record the resolved temp root and permission/mount evidence. In an isolated,
quiescent rehearsal environment, inventory that root before and after complete
downloads and the negative request; confirm no new request workspaces or response
archives remain. Do not delete files in a shared service to make a check pass.
`tests/test_api_tempdir.py` simulates unwritable candidates; passing it does not
prove deployed UID/mount permissions. Never make the live temp directory
unwritable to inject a failure.

## Restore and rehearse the previous known-good image

The platform and owner are unresolved, so there is deliberately no fabricated
ECS/Kubernetes/Compose production command here. The release owner must fill the
exact platform command or approved runbook link and resource ID in the record
before execution. A source revert or fresh image build is not image rollback.

1. Before rollout, capture the current running digest and configuration plus
   health and all smoke results. Verify they match the previous known-good record.
   Record the rollback trigger, observation window, operator and expected recovery
   time with the owner. Failures in health, contract/content, runtime permissions,
   cleanup, or unexpected image identity block promotion.
2. In the approved rehearsal environment, use the approved process to select the
   candidate by immutable digest and the recorded compatible configuration. Record
   the operation/revision ID; wait for platform rollout completion, then verify
   the actual digest on every serving replica and run the checks above.
3. Restore the **previous recorded digest and its configuration** using that same
   platform's approved update/rollback process. Do not use `latest`, rebuild an
   old commit, publish a replacement image, or assume a workflow push changed the
   service. Preserve before/after platform status and timestamps.
4. Wait for rollout completion and confirm all serving replicas use the target
   digest/configuration. Repeat health, all three successful uploads, malformed
   ZIP rejection, and runtime permission/cleanup checks. Record elapsed recovery
   time and compare with the owner's target. A healthy old replica while new
   replicas fail is not a successful rollback.
5. If restoration fails, stop further changes, preserve logs and operation IDs,
   and hand off to the named owner using the incident procedure. Do not invent a
   second rollback target. If it succeeds, retain both evidence sets and record
   which revision is left running. Returning to the candidate is a separate
   approved action.

This image rollback does not undo external data/configuration changes. Resolve
any state or schema compatibility before rollout; no migration or data restore
is part of this procedure. A local rehearsal can validate mechanics but cannot
stand in for evidence from the agreed baseline environment.

## Short release checklist / Phase 0 exit gate

- [ ] Owner and environment explicitly agreed; exact approved process recorded.
- [ ] Source/build/digest/running-revision chain and configuration recorded.
- [ ] Previous known-good image/configuration retained and pullable.
- [ ] Health, CSV ZIP, JSON ZIP, JSON multipart and failure recovery pass there.
- [ ] Runtime temp permissions and post-request cleanup verified there.
- [ ] Authorized rollback rehearsed; restored digest/configuration and smoke
  results recorded, with recovery time and final running state.
- [ ] Owner signs off and links the durable evidence from the Linear project
  and BLU-12. Only then mark this checkpoint complete; merging this runbook is
  not completion.

## Repository verification for this change

See [the local evidence record](baseline-release-local-evidence.md). Its results
are scoped to this checkout and test environment, not an approved release.
