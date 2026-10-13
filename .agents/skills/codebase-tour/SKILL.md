---
name: codebase-tour
description: Explain a Blueprint repository or trace a requested feature through its entry points, data flow, tests, and checks. Use for onboarding or navigation, not to propose an unsolicited rewrite.
---

# Codebase tour

1. Record the repository and revision. Read its instructions, README, manifests, and existing glossary before following imports or routes.
2. Trace one concrete user action from input to output. Cite the entry point, the modules doing the work, and the public interfaces between them. Follow the implementation far enough to distinguish current behavior from planned behavior.
3. Point to the tests covering that path and the configured local checks. Identify important state, external dependencies, and the nearest unverified boundary.
4. Return a short path map and a useful starting file for the user's next task. Label source-derived conclusions separately from behavior you actually exercised. State missing sources or runtime access explicitly.

Keep the tour read-only unless a documentation change was requested. Capture durable new knowledge with the existing team document rather than generating a duplicate architecture manual.

For provenance and adaptation details, see [sources](references/sources.md).
