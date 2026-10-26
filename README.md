# HSDS Transformer

## Development setup

### Dependency setup

Use Python 3.13 or newer and uv 0.11.21. Install uv with `python3 -m pip install uv==0.11.21` on macOS/Linux or `python -m pip install uv==0.11.21` on Windows. Run the following from the repository root. `uv` creates `.venv` when needed.

On Windows, pip may install `uv.exe` to `%APPDATA%\Python\Python313\Scripts`, which is not on PATH by default. If `uv` is not found, add that folder to PATH or run uv as `python -m uv` (for example, `python -m uv sync --locked --extra api`).

```bash
# Core CLI environment
uv sync --locked --no-default-groups

# API runtime without developer or audit tools
uv sync --locked --no-default-groups --extra api

# Development environment: API, tests, and Ruff
uv sync --locked --extra api
```

`pyproject.toml` declares direct dependencies and `uv.lock` is the authoritative resolution. The default `dev` group is included in the development command. The `requirements.txt` file is a generated pip compatibility export that includes API and development dependencies. Do not edit it by hand. Regenerate it with:

```bash
uv export --locked --format requirements.txt --extra api --no-default-groups --group dev --no-emit-project --output-file requirements.txt
```

For pip-only environments, install the generated export with `python -m pip install -r requirements.txt`.

The locked core and API runtime was audited with `pip-audit==2.10.1` on 2026-10-11. The audit found no known vulnerabilities, so there are no advisory IDs or affected package paths to report. Tests still emit a Starlette deprecation warning for using `httpx` with `TestClient`; it is not a vulnerability finding and remains in place.

## Running the command line tool

### Transformation
**Transforms CSVs into HSDS-compliant objects given proper associated mapping.**

Move the csv files to be transformed with their associated mapping (csv) files (see the [mapping docs](https://docs.google.com/document/d/1TEvuGkecCbyyGD8xI6ROholbTnlC-m260hQNx-BqP2w/edit?usp=sharing) and [mapping template](https://docs.google.com/spreadsheets/d/1zhYwVo1Lx2vQHSMQ71zkwVgB3RmWNnC-cuGa2qQqOew/edit?gid=0#gid=0)) into a directory (if you're testing in this repository, create a folder for your files in the data folder). See the current `data` folder for examples.

Make sure you're in the root folder.

```bash
# macOS/Linux (bash/zsh)
# Transform CSVs to HSDS JSON
uv run --locked --extra api python3 -m src.cli.main path/to/datadir
```

```Powershell
# Windows (PowerShell/cmd)
# Transform CSVs to HSDS JSON
uv run --locked --extra api python -m src.cli.main path\to\datadir
```

Options:
- _-o path/to/output/directory_: (optional) specifies an output directory. Without specifying, the transformer will create one in your root directory or add the files to `output` if it already exists.
- _-f {json/csv}_: (optional) specifies a file type for the input/mapping files. Defaults to csv but can be either csv or json.
- _--generate-ids {organization name/id}_: (optional) generates new standardized UUID-5 ids based on the name/id of the organization doing the transforming. Stores the old id in the attributes field. by default, preserves original IDs from the source data.
- _--transforms path\to\custom\_transforms.py_: (optional) enables the user to load their custom transform functions. Omitting this option is supported only when mappings declare no custom transforms.

### Custom transform compatibility policy

CSV and JSON CLI runs execute named transforms from a local Python module:

```python
transforms = {"uppercase": str.upper}
```

Use `--transforms path/to/transforms.py` with either input format. The module must
define a dictionary with nonempty string names and callable values. All declared
names are checked before any records are transformed, including declarations on
blank values or filtered records. A missing module, malformed registry, missing
name, or declaration without a registry fails the run. There is no silent-skip or
legacy fallback; older mappings relying on skipping must remove the declaration
or supply its implementation.

CSV and JSON mappings also reject conflicting output paths before processing
records. Duplicate destinations, a leaf alongside its descendant (such as
`value` and `value.nested`), and inconsistent object/array declarations now fail
with the mapping file and offending output path. Remove or disambiguate these
declarations instead of relying on their order to choose a winner.

Runtime failures retain the transform name, source and mapping files, zero-based
parsed record index, input path, and original exception. Existing blank-value
omission and split behavior are preserved; transforms on split leaves receive the
existing split result, and aligned input paths are transformed individually.
The API does not load uploaded Python modules; mappings requiring unavailable
custom transforms are rejected. Local modules execute Python during import and
must come from a trusted source.

Run regression tests with `python -m pytest tests/`.

### Reverse Transformation
**Reverse transform (HSDS JSON to CSV inputs).**

```bash
# macOS/Linux (bash/zsh)
uv run --locked --extra api python3 -m src.cli.reverse_transform --mapping-dir path/to/mappings --hsds-dir path/to/hsds-json --output-dir path/to/output
```

```bash
# Windows (PowerShell/cmd)
uv run --locked --extra api python -m src.cli.reverse_transform --mapping-dir path\to\mappings --hsds-dir path\to\hsds-json --output-dir path\to\output
```

The output directory is optional and defaults to `reverse_output`.

### Sanity Check

To confirm that the transformer is functioning correctly, you can run it against the included `sanity_check` dataset.

**Bash:**
```bash
uv run --locked --extra api python3 -m src.cli.main data/sanity_check
```

**Powershell:**
```Powershell
uv run --locked --extra api python -m src.cli.main data\sanity_check
```

### Unit Tests
Run the full pytest suite with the locked development dependencies:

```bash
uv run --locked --extra api python -m pytest tests/ -v
```

Run Ruff with the version from the lock:

```bash
uv run --locked --extra api ruff check .
```

### Generate mapping template from schema (HSDS schema to CSV template).
**From a GitHub URL**
This uses the `src.cli.maintenance` module with the `generate-mapping` subcommand. It validates the URL, fetches the schema, flattens it, and writes a mapping template CSV to your current working directory.

- Bash: `uv run --locked --extra api python3 -m src.cli.maintenance generate-mapping --github-url <github-url>`
- Powershell: `uv run --locked --extra api python -m src.cli.maintenance generate-mapping --github-url <github-url>`

The output file is named `{schema_name}_mapping_template.csv` (using the schema's `name` field), after sanitizing to a safe lowercase filename. If `name` is missing/empty after sanitization, it falls back to `{filename}_mapping_template.csv` from the URL path. For example:

```bash
uv run --locked --extra api python3 -m src.cli.maintenance generate-mapping \
  --github-url "https://raw.githubusercontent.com/openreferral/specification/refs/heads/3.2/schema/compiled/organization.json"
# → writes organization_mapping_template.csv to the current directory
```

If the target output file already exists, the command fails instead of overwriting it.

## Running the api

```bash
# All Platforms
# Start the FastAPI server
uv run --locked --extra api uvicorn src.api.app:app --reload
```

In a second terminal, verify the server is healthy:

```bash
# macOS/Linux
curl --fail http://localhost:8000/health

# Windows (PowerShell)
curl.exe --fail http://localhost:8000/health
```

Successful transformations from both `POST /transform` (CSV or JSON ZIP uploads)
and `POST /transform/stream` (JSON multipart uploads) return **201 Created** with
an `application/zip` response and
`Content-Disposition: attachment; filename=transformed.zip`.

### Running with Docker Compose

The container runs the same `src.api.app:app` module as the local `uvicorn`
command above; `APP_MODULE` is defined once in the Dockerfile and Compose
does not override it.

```bash
# macOS/Linux (bash/zsh)
# Build and start the API container
docker compose up --build -d

# Verify the container is healthy
curl --fail http://localhost:8000/health

# Exercise the transform endpoint through the running container
curl -X POST http://localhost:8000/transform \
  -F "zip_file=@data/sal_example.zip" \
  --output transformed.zip

# Inspect logs if something looks wrong
docker compose logs api

# Tear down
docker compose down
```

```bash
# Windows (PowerShell/cmd)
# Build and start the API container
docker compose up --build -d

# Verify the container is healthy
curl.exe --fail http://localhost:8000/health

# Exercise the transform endpoint through the running container
curl.exe -X POST http://localhost:8000/transform -F "zip_file=@data/sal_example.zip" --output transformed.zip

# Inspect logs if something looks wrong
docker compose logs api

# Tear down
docker compose down
```

### Endpoint regression tests

Run the endpoint contract regression tests using the checked-in CSV and JSON fixtures:

```bash
uv run --locked --extra api python -m pytest tests/test_api_transform.py -v
```

### Streaming transform endpoint

`POST /transform/stream` accepts `multipart/form-data` with repeated `files`
parts containing source JSON files and their matching `*_mapping.json` files.
The API stages the uploaded files in a temporary workspace, runs the JSON
transformer, and returns `application/zip` with the transformed HSDS JSON files.

```bash
curl -X POST http://localhost:8000/transform/stream \
  -F "files=@path/to/source.json" \
  -F "files=@path/to/source_mapping.json" \
  --output transformed.zip
```

If you deploy in an environment where default temp directories are not writable
(for example, some ECS task configurations), set `HSDS_TMP_DIR` to a writable
path before starting the API.

### Output identity validation (BLU-31)

Before creating the output directory or writing any files, the JSON writer checks
all supplied groups for nonempty IDs and duplicate output filenames. Missing,
null, empty, whitespace-only, and other false-valued IDs raise `ValueError`.
Duplicate errors identify both group/record positions. IDs are not generated,
trimmed, or deduplicated by the writer; valid output names and JSON stay unchanged.
An invalid identity anywhere in the supplied groups leaves existing files intact.

This is writer-level validation. BLU-16 must preserve repeated entity-type groups
through `searching_and_assigning` so all source records reach this check through
the CLI/API. Until that fix lands, earlier same-type source groups can still be
lost upstream. This change does not resolve that separate issue.

Existing-file replacement, stale-output handling, atomic publication, I/O-failure
rollback, and artifact accounting remain BLU-23 work. This preflight does not
promise atomic writes or enforce final HSDS ID formats.

Run the focused checks with `uv run --locked --extra api python -m pytest tests/test_outputs.py`;
run the full suite with `uv run --locked --extra api python -m pytest tests/` and lint with
`uv run --locked --extra api ruff check .`.
