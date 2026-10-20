# HSDS Transformer

## Setup

### Environment Setup

```bash
# macOS/Linux (bash/zsh)
# Create a virtualenv
python3 -m venv .venv

# Activate the virtualenv
source .venv/bin/activate

# Install dependencies using pip or uv
pip3 install -r requirements.txt

# OR
pip3 install uv
uv sync
```

```bash
# Windows (PowerShell/cmd)
# Create a virtualenv
python -m venv .venv

# Activate the virtualenv
.venv\Scripts\activate

# Install dependencies using pip or uv
pip install -r requirements.txt

# OR
pip install uv
uv sync
```

## Running the command line tool

### Transformation
**Transforms CSVs into HSDS-compliant objects given proper associated mapping.**

Move the csv files to be transformed with their associated mapping (csv) files (see the [mapping docs](https://docs.google.com/document/d/1TEvuGkecCbyyGD8xI6ROholbTnlC-m260hQNx-BqP2w/edit?usp=sharing) and [mapping template](https://docs.google.com/spreadsheets/d/1zhYwVo1Lx2vQHSMQ71zkwVgB3RmWNnC-cuGa2qQqOew/edit?gid=0#gid=0)) into a directory (if you're testing in this repository, create a folder for your files in the data folder). See the current `data` folder for examples.

Make sure you're in the root folder.

```bash
# macOS/Linux (bash/zsh)
# Transform CSVs to HSDS JSON
python3 -m src.cli.main path/to/datadir
```

```Powershell
# Windows (PowerShell/cmd)
# Transform CSVs to HSDS JSON
python -m src.cli.main path\to\datadir
```

Options:
- _-o path/to/output/directory_: (optional) specifies a new or empty output directory. Defaults to `output` in the current directory. A nonempty directory is refused with a clear error; existing files are never merged or overwritten.
- _-f {json/csv}_: (optional) specifies a file type for the input/mapping files. Defaults to csv but can be either csv or json.
- _--generate-ids {organization name/id}_: (optional) generates new standardized UUID-5 ids based on the name/id of the organization doing the transforming. Stores the old id in the attributes field. by default, preserves original IDs from the source data.
- _--transforms path\to\custom\_transforms.py_: (optional) enables the user to load their custom transform functions. Omitting this option is supported only when mappings declare no custom transforms.

### Output safety

Use a different destination for each run, for example
`python -m src.cli.main data/json_test -f json -o output/run-2`.
An existing empty directory is also accepted. Empty input publishes an empty
directory with zero artifacts; it still refuses a nonempty destination.

The writer checks all IDs and filename collisions before writing, then stages
the complete result beside the destination. IDs and object types must form a
single portable filename (no path separators, control characters or Windows
reserved punctuation). Non-JSON values, including NaN/infinity, fail explicitly.
Every staged JSON file is read back and its filename/count checked before the
complete directory is published. The CLI reports expected, written and verified
artifact counts; the API logs those counts and continues to return the same ZIP
format. Invalid output data returns HTTP 422; filesystem failures remain server
errors. Both API routes use a fresh destination for each request.

Handled failures remove staging and leave earlier output untouched. Publication
uses a same-filesystem directory rename, with a brief gap when replacing an empty
destination. A sibling `.DESTINATION.hsds-lock` excludes overlapping transformer
runs for the same destination. A crashed process can leave its lock and staging
directory behind; remove these only after confirming the process has stopped.
This does not guarantee recovery after power loss or protect against unrelated
processes changing the filesystem during publication.

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
python3 -m src.cli.reverse_transform --mapping-dir path/to/mappings --hsds-dir path/to/hsds-json --output-dir path/to/output
```

```bash
# Windows (PowerShell/cmd)
python -m src.cli.reverse_transform --mapping-dir path\to\mappings --hsds-dir path\to\hsds-json --output-dir path\to\output
```

The output directory is optional and defaults to `reverse_output`.

### Sanity Check

To confirm that the transformer is functioning correctly, you can run it against the included `sanity_check` dataset.

**Bash:**
```bash
python3 -m src.cli.main data/sanity_check
```

**Powershell:**
```Powershell
python -m src.cli.main data\sanity_check
```

### Unit Tests
Additionally, run unit tests for various features.

**Bash:**
```bash
python -m src.cli.unit_tests --tests {tests separated by space}
```

**Powershell:**
```Powershell
python -m src.cli.unit_tests --tests {tests separated by space}
```

Available tests: all, test_transformer, test_sanity, test_mapping_template, test_mapping_cli

### Generate mapping template from schema (HSDS schema to CSV template).
**From a GitHub URL**
This uses the `src.cli.maintenance` module with the `generate-mapping` subcommand. It validates the URL, fetches the schema, flattens it, and writes a mapping template CSV to your current working directory.

- Bash: `python3 -m src.cli.maintenance generate-mapping --github-url <github-url>`
- Powershell: `python -m src.cli.maintenance generate-mapping --github-url <github-url>`

The output file is named `{schema_name}_mapping_template.csv` (using the schema's `name` field), after sanitizing to a safe lowercase filename. If `name` is missing/empty after sanitization, it falls back to `{filename}_mapping_template.csv` from the URL path. For example:

```bash
python3 -m src.cli.maintenance generate-mapping \
  --github-url "https://raw.githubusercontent.com/openreferral/specification/refs/heads/3.2/schema/compiled/organization.json"
# → writes organization_mapping_template.csv to the current directory
```

If the target output file already exists, the command fails instead of overwriting it.

## Running the api

```bash
# All Platforms
# Start the FastAPI server
uvicorn api.app:app --app-dir src --reload
```

Successful transformations from both `POST /transform` (CSV or JSON ZIP uploads)
and `POST /transform/stream` (JSON multipart uploads) return **201 Created** with
an `application/zip` response and
`Content-Disposition: attachment; filename=transformed.zip`.

### Running with Docker Compose

The container runs the same `api.app:app` module as the local `uvicorn`
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
uv sync --extra api --extra dev
uv run --extra api --extra dev pytest tests/test_api_transform.py
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

Run the focused checks with `python -m pytest tests/test_outputs.py`; run the full
suite with `python -m pytest tests/` and lint with `uvx ruff==0.16.8 check .`.
