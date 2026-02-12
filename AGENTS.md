# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the Python package.
- `src/lib/` holds core transformation logic (parsing, mapping, relations, outputs).
- `src/cli/` contains the Click-based command line entry points.
- `src/api/` contains the FastAPI app and middleware.
- `data/` provides sample datasets and mapping CSVs for reference.

## Build, Test, and Development Commands
- `python3 -m venv .venv` and `source .venv/bin/activate` (macOS/Linux) to create and activate a virtualenv.
- `pip3 install -r requirements.txt` to install base dependencies.
- `pip3 install uv` then `uv sync` to install dependencies via `uv`.
- `python3 -m src.cli.main path/to/datadir` to transform CSVs into HSDS JSON.
- `python3 -m src.cli.main path/to/datadir path/to/outputdir` to specify output.
- `python3 -m src.cli.reverse_transform --mapping-dir path/to/mappings --hsds-dir path/to/hsds-json --output-dir path/to/output` for the reverse transform (currently WIP).
- `uvicorn api.app:app --app-dir src --reload` to run the FastAPI server locally.

## Coding Style & Naming Conventions
- Use Python 3.13+ and standard library idioms (project uses `glom` and `click`).
- Follow existing module naming and file structure under `src/`.
- Mapping files must be named `<input_filename>_<object_type>_mapping.csv`.
- Keep transformations explicit; avoid hidden side effects in mapping or relation logic.

## Testing Guidelines
- No dedicated test framework or test directory is present.
- If you add tests, prefer `tests/` with `pytest`-style naming like `test_parser.py` and document how to run them.

## Commit & Pull Request Guidelines
- Recent history uses short, action-oriented subjects (e.g., `fix handling of unzipped files`) plus GitHub merge commits.
- Until a formal convention is adopted, use concise imperative subjects and keep PR titles descriptive.
- PRs should include: a summary, how to run the change locally, and any sample data or mappings used (e.g., `data/simple_mapping/`).

## Configuration & Data Tips
- Input directories must include both source CSVs and their mapping CSVs.
- The transformer outputs HSDS JSON to `output/` by default.
- The API `POST /transform` expects a `.zip` containing CSVs and mappings and returns a `.zip` of HSDS JSON.
