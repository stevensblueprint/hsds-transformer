# Transformer log: cross-request accumulation (BLU-10 prep)

Diagnostic note for the regression in
`tests/test_api_transform_log_isolation.py`. This is not the BLU-10 fix. It
changes no production code and does not clear the singleton.

## Problem

`src/lib/transform/logger.py` defines one module-level `transformer_log`.
`build_collections`, `build_collections_from_json` and `searching_and_assigning`
all append to it. The CLI calls `transformer_log.clear()` before each run. The
API (`/transform`, `/transform/stream`) never clears it, and it can't safely
do so, because concurrent requests share the same object. So in a long-lived
API process, each request's log holds every earlier request's entries.

## Evidence (2026-10-20, local tree based on `d6a3191`)

The probe sends two sequential `/transform` requests, each with a
one-organization synthetic CSV dataset (`alpha`, then `beta`), through
`TestClient` in a fresh process:

| Point            | `len(transformer_log.entries)` | `id(transformer_log)` |
|------------------|-------------------------------:|-----------------------|
| before requests  | 0                              | same                  |
| after `alpha`    | 16                             | same                  |
| after `beta`     | 32                             | same                  |

After `beta`, the log still holds `alpha`'s lines: its `Input directory:`
line and `organization: 1 object(s) from alpha.csv`. Each request adds exactly
16 entries, and none are dropped. An earlier report saw growth from 25 to 50 at
`0a719c1` with a larger dataset. That figure is historical and was not rerun.
The absolute count depends on how many collections the dataset has, so the
test checks request markers instead of counts.

`--runxfail` output from the regression (stream case, run after the transform
case in the same process):

```
AssertionError: 2 entries from the first request leaked:
  ['  organization: 1 object(s) from REQ-ALPHA.csv',
   '  organization: 1 object(s) from REQ-ALPHA.json']
```

The `.csv` entry was left by a *different test*. This shows the leak spans the
whole process, not just one client.

## Regression contract

- Two parametrized cases (`/transform` CSV, `/transform/stream` JSON). Each
  sends two requests whose uploaded filenames carry `REQ-ALPHA` / `REQ-BETA`.
  Uppercase letters and hyphens never appear in temp-dir names, so a marker
  can only reach the log through the request's own input.
- `xfail(strict=True, raises=AssertionError)`, linked to BLU-10.
  - Today: `XFAIL`, which keeps default CI green.
  - When BLU-10 isolates the log: `XPASS(strict)`, which fails CI and forces the
    marker to be removed. (This was checked with a simulated per-request
    reset.)
  - Preconditions (status 201, own marker present) use `pytest.fail`. A broken
    request is therefore a real failure and is never absorbed as the expected
    one. (This was checked by forcing a 413.)
- When BLU-10 lands, point the assertion at the new seam (below) rather than
  at the module global.

## Proposed request-state seam (smallest)

The smallest seam is to pass the log in explicitly, and have the request own
it:

```python
# lib/transform/collections.py, json_collections.py
def build_collections(data_directory, log: TransformerLog | None = None): ...
def build_collections_from_json(data_directory, log: TransformerLog | None = None): ...
def searching_and_assigning(results, log: TransformerLog | None = None): ...
#   log = log if log is not None else transformer_log   # CLI default unchanged

# api/app.py, per request
log = TransformerLog()
results = build_collections(input_dir, log=log)
results = searching_and_assigning(results, log=log)
```

- The change touches 3 library functions and 2 endpoints. The CLI keeps the
  module default (and its existing `clear()`), so CLI behavior does not change.
- The request owns `log`, and the log is discarded once the response is built.
  The test can then assert on the per-request log, for example by exposing it
  through a small helper or a `request.state` attribute. It no longer needs to
  inspect the global.
- An explicit parameter is preferred over a `ContextVar`. Only three call
  sites need it, and an explicit argument stays correct if the pipeline is
  later moved to a threadpool or a background task.
- Out of scope here: removing the global entirely, concurrency guarantees, and
  surfacing the log in the API response.

## Follow-on cleanup test matrix (for BLU-10)

Each row should assert two things. First, the failing request's log does not
appear in the next successful request's log. Second, nothing the request
created under `HSDS_TMP_DIR` is left behind.

| Scenario                | How to trigger                                                    | Expected response | Log isolation        | Temp cleanup                           |
|-------------------------|-------------------------------------------------------------------|-------------------|----------------------|----------------------------------------|
| Malformed zip           | non-zip bytes / `BadZipFile`                                      | 422               | no entries leak      | no `hsds-input-*` left                 |
| Malformed mapping/input | mapping references a missing column (`ValueError`)                | 422               | partial log discarded| input dir removed                      |
| Transformation failure  | monkeypatch `searching_and_assigning` to raise                    | 500               | partial log discarded| input dir removed                      |
| Write failure           | monkeypatch `save_objects_to_json` / zip write to raise `OSError` | 500               | partial log discarded| output dir + `*.zip` removed           |
| Interrupted download    | close the streamed response after the first chunk                 | n/a (client gone) | n/a                  | `_iter_and_cleanup` `finally` runs; zip removed |

The last row records the behavior to test. It makes **no claim** about whether
the current code leaks on disconnect. That is for BLU-10 to verify.
