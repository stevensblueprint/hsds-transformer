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
- _-o path/to/output/directory_: (optional) specifies an output directory. Without specifying, the transformer will create one in your root directory or add the files to `output` if it already exists.
- _-f {json/csv}_: (optional) specifies a file type for the input/mapping files. Defaults to csv but can be either csv or json.
- _--generate-ids {organization name/id}_: (optional) generates new standardized UUID-5 ids based on the name/id of the organization doing the transforming. Stores the old id in the attributes field. by default, preserves original IDs from the source data.
- _--transforms path\to\custom\_transforms.py_: (optional) enables the user to load their custom transform functions. If no `custom_transforms.py` file is specified, the transformer will run normally.

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
python -m src.cli.unit-tests --tests {tests separated by space}
```

**Powershell:**
```Powershell
python -m src.cli.unit-tests --tests {tests separated by space}
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

### Streaming transform endpoint
`POST /transform` accept a zip file containing input and mapping files and returns a zip file with the transformed HSDS JSON files.  

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
