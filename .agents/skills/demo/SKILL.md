---
name: demo
description: Prepare or run a reproducible Blueprint change demo with observed user-facing results. Use for a requested walkthrough or runtime evidence; a demo plan alone does not establish that behavior works.
---

# Demo

1. Name the behavior and expected outcome from the human requirement. Record the build/commit, prerequisites, safe sample inputs, startup command, and cleanup. Derive commands and routes from the current repository.
2. Use an isolated local/test instance and verify readiness and identity before driving it. For a UI change, use the UI through its API to the resulting state or downloaded artifact; for a CLI/API change, use that actual public entry point. Record any simulated external boundaries.
3. Capture the input/action and inspect the observable result: displayed state, response, output contents, or persisted effect as relevant. A screenshot, HTTP success, archive check, or build alone cannot prove the whole flow.
4. Add the relevant failure, retry, or interruption scenario from the verification plan. If no plan exists, select the nearest consequential failure case; avoid an exhaustive ritual for a small change.
5. Save evidence before cleanup; stop only instances you started and preserve evidence files. Report `PASS`, `FAIL`, or `NOT RUN` for each scenario, with revision, steps, artifact paths, and limitations. If startup or access blocks execution, deliver a clearly labeled unrun script and the blocker.

Reuse an existing verification report when available; keep only demo-specific steps and evidence here. Use synthetic or approved fixtures, with no secrets in captures. This skill authorizes no deployment or publication.

For provenance and adaptation details, see [sources](references/sources.md).
