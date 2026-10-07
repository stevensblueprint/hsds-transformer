# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the Python package.
- `src/lib/` holds core transformation logic (parsing, mapping, relations, outputs).
- `src/cli/` contains the Click-based command line entry points.
- `src/api/` contains the FastAPI app and middleware.
- `data/` provides sample datasets and mapping CSVs for reference.

## Build, Test, and Development Commands

### Environment Setup
```bash
# macOS/Linux (bash/zsh)
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (preferred method)
pip3 install uv
uv sync

# Alternative: install with pip
pip3 install -r requirements.txt
```

```bash
# Windows (PowerShell/cmd)
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies (preferred method)
pip install uv
uv sync

# Alternative: install with pip
pip install -r requirements.txt
```

### Running the CLI
```bash
# macOS/Linux (bash/zsh)
# Transform CSVs into HSDS JSON
python3 -m src.cli.main path/to/datadir
python3 -m src.cli.main path/to/datadir -o path/to/outputdir

# Reverse transform (currently WIP)
python3 -m src.cli.reverse_transform --mapping-dir path/to/mappings --hsds-dir path/to/hsds-json --output-dir path/to/output
```

```bash
# Windows (PowerShell/cmd)
# Transform CSVs into HSDS JSON
python -m src.cli.main path\to\datadir
python -m src.cli.main path\to\datadir -o path\to\outputdir

# Reverse transform (currently WIP)
python -m src.cli.reverse_transform --mapping-dir path\to\mappings --hsds-dir path\to\hsds-json --output-dir path\to\output
```

### Running the API
```bash
# All Platforms
# Run the FastAPI server locally
uvicorn api.app:app --app-dir src --reload
```

## Coding Style & Naming Conventions
- Use Python 3.13+ and standard library idioms (project uses `glom` and `click`).
- Follow existing module naming and file structure under `src/`.
- Mapping files must be named `<input_filename>_<object_type>_mapping.csv`.
- Keep transformations explicit; avoid hidden side effects in mapping or relation logic.

## Testing Guidelines
- Tests use `pytest` and live in `tests/`; follow the existing `test_*.py` naming. `pyproject.toml` configures the import paths.
- From the repository root in an activated Python 3.13+ environment, use the same dependencies and checks as CI:
  ```bash
  python -m pip install -r requirements.txt
  python -m pip install ruff==0.16.8
  ruff check --output-format=github .
  python -m pytest tests/ -v
  ```
- `.github/workflows/ruff.yml` pins Ruff; `pyproject.toml` selects `E4`, `E7`, `E9`, and `F`. `.github/workflows/unit-tests.yml` runs pytest with Python 3.13.
- For the uv setup, include the API and test dependencies with `uv sync --extra api --extra dev`, then run `uv run --extra api --extra dev pytest tests/ -v` (Ruff is installed separately above).
- Choose checks for the changed behavior: use a focused regression test while iterating, then the suite for code changes. For CLI/API or packaging changes, also exercise the affected path with checked-in sample data and inspect the output. `.github/workflows/docker-smoke.yml` provides a Docker health/transform smoke recipe; archive validity alone does not prove the transformed contents are correct.
- Cover malformed input, repeated requests, or interrupted work when the change affects those cases. A docs-only change can use source/command consistency checks and `git diff --check`; record omitted runtime checks.
- Report the checked commit (and any uncommitted changes), commands, observed results, and evidence paths. Mark each check `PASS`, `FAIL`, or `NOT RUN` with the reason for failures or omissions; distinguish unit/static checks from end-to-end behavior.

## Commit & Pull Request Guidelines
- Recent history uses short, action-oriented subjects (e.g., `fix handling of unzipped files`) plus GitHub merge commits.
- Until a formal convention is adopted, use concise imperative subjects and keep PR titles descriptive.
- PRs should include: a summary, how to run the change locally, and any sample data or mappings used (e.g., `data/simple_mapping/`).

## Configuration & Data Tips
- Input directories must include both source CSVs and their mapping CSVs.
- The transformer outputs HSDS JSON to `output/` by default.
- The API `POST /transform` expects a `.zip` containing CSVs and mappings and returns a `.zip` of HSDS JSON.
