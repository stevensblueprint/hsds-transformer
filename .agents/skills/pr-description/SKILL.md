---
name: pr-description
description: Draft or update a Blueprint pull request description from the actual diff and recorded verification evidence. Does not write a PRD, submit review comments, or grant permission to publish or merge.
---

# PR description

1. Read the repository's PR template, the human-written requirement, and the complete diff from a named base to the candidate head. Resolve the exact commits; include uncommitted changes if present.
2. Lead with the problem and resulting behavior. Explain the meaningful changes and any compatibility or rollout limitation. Use a small before/after example or visual only when it clarifies the change.
3. Carry forward the evidence report: exact tested revision, commands or actions, `PASS` / `FAIL` / `NOT RUN`, evidence locations, and material gaps. Distinguish a proposed demo from one actually run. Preserve failures and missing evidence even when CI is green.
4. Re-read the draft against the final diff. Remove obsolete plans and unsupported claims. Keep a small documentation PR to a short explanation and relevant validation.

Blueprint PRDs and review comments stay human-written. Supply factual evidence for their authors; do not manufacture review approvals, quotations, or acceptance decisions. Produce a local draft unless posting is already authorized; this skill provides no publish, merge, or release permission.

For provenance and adaptation details, see [sources](references/sources.md).
