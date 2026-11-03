# Blueprint skills provenance

Recovered from the local `blueprint-agents` collection prepared on 2026-10-07,
commit `2ed2493ad70b2b4add14dd0022a387ec01aef079`, tree
`dbbcd737d3e853d4647de16703fedd957b585813`. The collection had no remote;
the original checkout and review archive are preserved outside this repository.
The seven original skill folders, metadata, source notes, and upstream MIT notices
were copied before adapting them here. No separate repository is required.

Adapted on 2026-10-13 for `stevensblueprint/hsds-transformer` at
`2484fa79b64dca1e18d738ec95ce1b7ca22e4d57`:

- Added repository routing and explicit invocation examples in `AGENTS.md`.
- Replaced the old backend/UI command snapshot with links to this repository's
  current instructions and executable configuration. The UI is a separate project.
- Linked verification to Testing Guidelines from merged
  [PR #150](https://github.com/stevensblueprint/hsds-transformer/pull/150), leaving that section unchanged.
- Added `blueprint-research`, authored for this migration, for sourced investigation
  and explicit uncertainty. It copies no additional third-party source.
- Retained pstack's selected verification ideas and original notices, without
  introducing a pstack runtime, tool dependency, or shipping workflow.

The historical inventory below records what informed the recovered work; its
repository-state statements are snapshots, not current setup instructions.

## Original source inventory

Read on 2026-10-07 from fresh isolated clones:

- [Matt Pocock skills](https://github.com/mattpocock/skills/tree/f3fc5632f401156837ee3872f14fe33ccf1024ea), revision `f3fc5632f401156837ee3872f14fe33ccf1024ea`, MIT, copyright 2026 Matt Pocock. Consulted domain-modeling, codebase-design, code-review, tdd, and pr. The PR source's Dex Horthy / Humanlayer credit is preserved in the corresponding draft's provenance.
- [pstack by Lauren Tan / poteto](https://github.com/cursor/plugins/tree/d0ef80d86795816da932a153458c5dbe192d294e/pstack), cursor/plugins revision `d0ef80d86795816da932a153458c5dbe192d294e`, MIT, copyright 2026 Lauren Tan. Consulted create-verification-skill, maintain-verification-skill, prove-it-works, test-behavior-not-implementation, and make-operations-idempotent. Selected ideas were condensed; orchestration and ship/merge workflows were not imported.
- [HSDS backend](https://github.com/stevensblueprint/hsds-transformer/tree/242b283820baabd6bb34862f064fcab91a9f2ec9), revision `242b283820baabd6bb34862f064fcab91a9f2ec9`: AGENTS.md, pyproject.toml, requirements.txt, README.md, tests, and GitHub workflows. Live main was verified to include merged PR #146 removing Assign Coding Buddy.
- [HSDS UI](https://github.com/stevensblueprint/hsds-transformer-ui/tree/c131c48b98a0429197b6f83b61a0198946fdaec7), revision `c131c48b98a0429197b6f83b61a0198946fdaec7`: package.json, build workflow, ESLint and TypeScript settings, README, and source layout.

Neither Blueprint repository has `.agents/skills` at these revisions; the UI also has no AGENTS.md. Installed skill-creator and writing-for-agents guidance informed packaging and validation. Installed tdd and codebase-design were inspected as local design context; adaptations are attributed to the public upstream revisions above.

Complete upstream MIT notices travel inside each skill that adapts that source so standalone copying preserves attribution. Source-specific adaptation notes are in each skill's `references/sources.md`. No private work documents were copied.
