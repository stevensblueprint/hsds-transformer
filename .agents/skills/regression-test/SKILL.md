---
name: regression-test
description: Reproduce a Blueprint bug and add focused behavior tests that catch it through a public interface. Use for a defect or a changed contract; avoid tests that merely pin prose or implementation structure.
---

# Regression test

1. State the reported trigger and expected observable result. Use the existing test framework and fixtures; choose the smallest public interface that exposes the defect. Derive expected values from the contract or a worked example, not the implementation under test.
2. Reproduce the failure before changing code when possible. Save the failing command and output. If the old revision cannot run or the fix already exists, disclose the missing before evidence; never label an imagined failure as observed.
3. Add one focused test; change product code only when the user's task includes fixing the defect. Assert the returned contents or effect, not merely that a mock was called. Keep external substitutions explicit and avoid mocking away the behavior under examination.
4. Select nearby cases by risk: normal and malformed input for validation; a second request for reuse/state leakage; retry or interruption/recovery for lifecycle changes. Check the promised result and cleanup after each, rather than requiring every category for every bug.
5. Run the focused test, then the relevant existing suite. Record exact revisions, commands, `PASS` / `FAIL` / `NOT RUN`, and output paths. An expected failure on the old revision is useful reproduction evidence; distinguish it from a failing candidate.

If no framework exists, report that gap and provide a reproducible check using existing tools; do not invent an `npm test` command. Leave unrelated bugs and new test infrastructure outside scope unless authorized.

For provenance and adaptation details, see [sources](references/sources.md).
