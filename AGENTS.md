# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the Python package.
- `src/lib/` holds core transformation logic (parsing, mapping, relations, outputs).
- `src/cli/` contains the Click-based command line entry points.
- `src/api/` contains the FastAPI app and middleware.
- `data/` provides sample datasets and mapping CSVs for reference.

## Build, Test, and Development Commands

### Environment Setup
See [README.md#dependency-setup](README.md#dependency-setup) for the pinned uv version, locked core/API/development commands, and generated pip export instructions.

### Running the CLI
```bash
# macOS/Linux (bash/zsh)
# Transform CSVs into HSDS JSON
uv run --locked --extra api python3 -m src.cli.main path/to/datadir
uv run --locked --extra api python3 -m src.cli.main path/to/datadir -o path/to/outputdir

# Reverse transform (currently WIP)
uv run --locked --extra api python3 -m src.cli.reverse_transform --mapping-dir path/to/mappings --hsds-dir path/to/hsds-json --output-dir path/to/output
```

```bash
# Windows (PowerShell/cmd)
# Transform CSVs into HSDS JSON
uv run --locked --extra api python -m src.cli.main path\to\datadir
uv run --locked --extra api python -m src.cli.main path\to\datadir -o path\to\outputdir

# Reverse transform (currently WIP)
uv run --locked --extra api python -m src.cli.reverse_transform --mapping-dir path\to\mappings --hsds-dir path\to\hsds-json --output-dir path\to\output
```

### Running the API
```bash
# All Platforms
# Run the FastAPI server locally
uv run --locked --extra api uvicorn api.app:app --app-dir src --reload
```
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
