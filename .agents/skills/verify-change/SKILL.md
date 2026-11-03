---
name: verify-change
description: Plan and report risk-based verification for a Blueprint change before handoff. Use when deciding what to check or assessing completion evidence, especially for changes spanning interfaces or stateful flows.
---

# Verify a change

Use the current [AGENTS Testing Guidelines](../../../AGENTS.md#testing-guidelines)
for this repository's commands and evidence requirements. This skill selects
checks for the task and organizes their evidence; it does not replace that guidance.

1. Resolve the repository, base and candidate commits, dirty diff, and human requirement. Read the affected paths, existing tests, and CI. List the few consequential ways the change could fail.
2. Pair each risk with the cheapest check that can observe it and a concrete expected result. Start with relevant static/unit checks; add integration or a real UI/CLI/API flow for affected boundaries. For documentation-only changes, check claims, links, commands, and the diff; explain why runtime checks are omitted.
3. Cover the normal path and applicable negative, regression, repeated, and interrupted/recovery paths. Select categories because the change touches validation, shared state, retries, or lifecycle; record relevant exclusions instead of running a fixed exhaustive checklist.
4. Run checks against the identified candidate in an isolated environment. Observe the final state/output as well as success signals. Label mocks and missing external services. Use existing test/demo recipes; add a helper only when it materially improves repeatability.
5. Complete the [evidence record](references/evidence.md). Mark each planned check `PASS`, `FAIL`, or `NOT RUN`; include command/action, observation, artifact path, and reason for any gap. Preserve evidence through cleanup.
6. Compare the candidate to the tested revision before handoff. If it changed, re-run affected checks or mark the earlier evidence stale. Stop when selected checks pass or remaining failures/blockers are precisely reported; do not expand into unrelated repairs.

The report supports a human decision. It does not imply review approval or permission to publish, merge, or release. PR descriptions and demos should reuse this report rather than maintain competing pass/fail summaries.

For provenance and adaptation details, see [sources](references/sources.md).
