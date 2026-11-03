---
name: coding-standards
description: Apply or explain the actual conventions of a Blueprint repository during code changes or standards review. Use repository instructions and tooling as evidence; do not invent organization-wide rules.
---

# Coding standards

1. Read the applicable `AGENTS.md`, contribution guide, existing `.agents/skills`, manifests, lint/type settings, and CI for the affected package. Distinguish enforced rules, documented conventions, and your suggestions.
2. Match nearby code where configuration is silent. Keep transformations explicit and interfaces small; put one responsibility in its existing home. Add abstractions for a demonstrated need, with tests observing their public behavior.
3. Run the configured checks for the changed package. Report unrelated baseline failures without widening the patch or changing CI/security settings to make checks pass.
4. Cite the configuration or file behind a claimed rule. If sources disagree, identify the discrepancy and follow current executable configuration for commands; propose a focused documentation correction.

For this backend, read the [repository check sources](references/hsds-checks.md) and verify them against the current checkout. Frontend commands belong to the separate UI repository. A successful lint or build is evidence for that check only.

For provenance and adaptation details, see [sources](references/sources.md).
