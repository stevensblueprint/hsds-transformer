# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the Python package.
- `src/lib/` holds core transformation logic (parsing, mapping, relations, outputs).
- `src/cli/` contains the Click-based command line entry points.
- `src/api/` contains the FastAPI app and middleware.
- `data/` provides sample datasets and mapping CSVs for reference.

## Build, Test, and Development Commands

Use the [contributor runbook](docs/contributor-runbook.md) as the canonical
Python 3.13 setup and CLI/API/Compose verification path. Dependency variants and
pip exports are documented in [README.md#dependency-setup](README.md#dependency-setup).
The API module is `src.api.app:app`; reverse transformation is partial and
non-gating for the forward path.

## Coding Style & Naming Conventions
- Use Python 3.13+ and standard library idioms (project uses `glom` and `click`).
- Follow existing module naming and file structure under `src/`.
- Mapping files must be named `<input_filename>_<object_type>_mapping.csv`.
- Keep transformations explicit; avoid hidden side effects in mapping or relation logic.

## Testing Guidelines
- Tests use pytest in `tests/` and follow the existing `test_*.py` naming. `pyproject.toml` configures import paths.
- From the repository root, use the locked API and development dependencies:
  - `uv sync --locked --extra api`
  - `uv run --locked --extra api python -m pytest tests/ -v`
  - `uv run --locked --extra api ruff check .`
- Run focused regressions while iterating, then the full suite. For CLI/API or packaging changes, run the relevant smoke checks and builds. Record the commands and results.

## Commit & Pull Request Guidelines
- Recent history uses short, action-oriented subjects (e.g., `fix handling of unzipped files`) plus GitHub merge commits.
- Until a formal convention is adopted, use concise imperative subjects and keep PR titles descriptive.
- PRs should include: a summary, how to run the change locally, and any sample data or mappings used (e.g., `data/simple_mapping/`).

## Configuration & Data Tips
- Input directories must include both source CSVs and their mapping CSVs.
- The transformer outputs HSDS JSON to `output/` by default.
- The API `POST /transform` expects a `.zip` containing CSVs and mappings and returns a `.zip` of HSDS JSON.

## Repository Skills

Reusable task guidance lives in `.agents/skills/`. Read the matching `SKILL.md`
when it applies; the skills supplement this file and do not grant publication,
merge, or deployment permission. Testing Guidelines above remain the source for
backend verification commands. Use only skills relevant to the current task.

| Skill | Use it for |
| --- | --- |
| [blueprint-knowledge](.agents/skills/blueprint-knowledge/SKILL.md) | Preserve sourced domain facts and decisions in existing documentation |
| [coding-standards](.agents/skills/coding-standards/SKILL.md) | Apply conventions supported by this checkout and its configuration |
| [pr-description](.agents/skills/pr-description/SKILL.md) | Describe the final diff and actual verification evidence |
| [demo](.agents/skills/demo/SKILL.md) | Exercise a public flow and retain observed results |
| [blueprint-research](.agents/skills/blueprint-research/SKILL.md) | Answer a technical question with sources and explicit uncertainty |
| [codebase-tour](.agents/skills/codebase-tour/SKILL.md) | Trace one feature through entry points, implementation, and tests |
| [regression-test](.agents/skills/regression-test/SKILL.md) | Reproduce a defect with meaningful behavior tests |
| [verify-change](.agents/skills/verify-change/SKILL.md) | Select proportionate checks and report their evidence |

In Codex, invoke a skill by name, for example: `Use $blueprint-research to explain
how mapping files become HSDS JSON`, `Use $verify-change on this diff`, or
`Use $pr-description to draft a description from this diff and verification report`.
If the client does not discover repository skills, ask it to read the linked
`SKILL.md` directly. No global installation or additional tool stack is needed.
See [provenance and retained upstream notices](.agents/SOURCES.md) for the recovered
Blueprint collection and its selected pstack and Matt Pocock adaptations.
