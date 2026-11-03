# HSDS Transformer

## Development setup

Start with the [contributor runbook](docs/contributor-runbook.md) for the Python 3.13
install, lint, full suite, CSV/JSON CLI, API, and Compose checks. It includes
expected responses, verification evidence, and outstanding acceptance gaps.

### Dependency setup

Use Python 3.13 or newer and uv 0.11.21. Install uv with `python3 -m pip install uv==0.11.21` on macOS/Linux or `python -m pip install uv==0.11.21` on Windows. Run the following from the repository root. `uv` creates `.venv` when needed.

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

Run regression tests with the [locked contributor commands](docs/contributor-runbook.md#install-and-check).

### Reverse Transformation
**Reverse transform (HSDS JSON to CSV inputs; partial/work in progress).**

Reverse transformation is non-gating for the forward contributor path. Do not
assume lossless round trips; pilot-specific reverse requirements need separate
fixtures and acceptance evidence.

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

Follow the [contributor runbook](docs/contributor-runbook.md) for both CSV and JSON
smoke checks, output assertions, the full pytest suite, and locked Ruff.

### Unit Tests

Use the [locked test and lint sequence](docs/contributor-runbook.md#install-and-check).

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
uv run --locked --extra api python -m uvicorn src.api.app:app --reload
```

ZIP uploads to `POST /transform` are limited to 5 MiB compressed, 1,000 members
(including directory entries), 20 MiB per expanded file, 50 MiB total expanded
bytes, and a 100:1 expanded/compressed ratio per member. These provisional
budgets bound disk use and extraction work: the total is ten times the upload
cap, individual files cannot consume the whole budget, and the member cap
bounds archive entries. They are conservative service defaults, not measured
production capacity. Split larger datasets; for highly compressible data, use
stored compression (subject to the 5 MiB upload cap).

Metadata is checked before extraction, and streamed bytes are checked before
writing beyond a budget. Budget violations return **413**; invalid paths,
encrypted entries, unsupported compression, conflicting paths, and corrupt
entries return **422**. Only regular files/directories with stored or deflated
compression are accepted. Absolute paths, parent traversal, backslashes, and
link entries are rejected. Failed extraction removes the request workspace and
creates no response ZIP. Normal nested folders remain supported.

Successful transformations from both `POST /transform` (CSV or JSON ZIP uploads)
and `POST /transform/stream` (JSON multipart uploads) return **201 Created** with
an `application/zip` response and
`Content-Disposition: attachment; filename=transformed.zip`.

### Running with Docker Compose

Use the [Compose runbook](docs/contributor-runbook.md#compose) for local build,
health and transform checks, output inspection, and teardown.

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

Run focused checks with `uv run --locked --extra api python -m pytest tests/test_outputs.py`;
use the [runbook](docs/contributor-runbook.md#install-and-check) for full-suite and lint commands.
