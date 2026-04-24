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

Move the csv files to be transformed with their associated mapping (csv) files into a directory (if you're testing in this repository, create a folder for your files in the data folder). See the current `data` folder for examples.

Make sure you're in the root folder.

```bash
# macOS/Linux (bash/zsh)
# Transform CSVs to HSDS JSON
python3 -m src.cli.main path/to/datadir -f csv
```

```bash
# Windows (PowerShell/cmd)
# Transform CSVs to HSDS JSON
python -m src.cli.main path\to\datadir
```

#### Options: 
- `-f [csv/json]` : (optional) specifies the type of ...
- `-o [path\to\outputdir]` : (optional) specifies an output directory. Without specifying an output directory, the transformer will create one in your root directory or add the files to `output` if it already exists.
- `--generate-ids [organization name or ID]` : (optional) will generate new standardized UUID-based IDs for all objects using the organization name or ID of the organization _doing the transformation_. Will store old ids in `attributes[].value`. By default, the transformer will preserves original IDs from the source data
- `--transforms [path\to\custom_transform.py]` : (optional) if custom transforms are defined and specified in the mapping template, include this flag and the path to the `custom_transforms.py` file

**Transform JSON files into HSDS compliant objects given associated mapping files**

Move the json files and mapping files into a directory, see data/json_test for an example. 

Make sure you're in the root folder (of repo)

```bash
python3 -m src.cli.main {path to datadir} -f json
python3 -m src.cli.main {path to datadir} -f json -o {path to output}
```

### Reverse transform (HSDS JSON to CSV inputs).

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

```bash
# macOS/Linux (bash/zsh)
python3 -m src.cli.main data/sanity_check
```

```powershell
# Windows (PowerShell/cmd)
python -m src.cli.main data\sanity_check
```

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

If you deploy in an environment where default temp directories are not writable
(for example, some ECS task configurations), set `HSDS_TMP_DIR` to a writable
path before starting the API.

## BRIEF PROCESS EXPLANATION

We create a collection of each of the HSDS files by going through each input file and doing the following:

parse the input file into a dictionary such as:

```
src = {
        "input_filename": {
            "entity_id": "org-123",
            "entity_name": "Acme Corp",
            "entity_description": "A fictional company",
            "Phone1Number": "123-456-8910",
            "Phone2Number": "098-765-4321"
        }
    }
```

and the mapping file into the form:

```
mapping = {
        "id": {"path": "organization.entity_id"},
        "name": {"path": "organization.entity_name", "strip": ["<p>","[","]"]}, # removes these sets of characters
        "description": {"path": "organization.entity_description", "split": ","}, # split into multiple objects
        "phones": [
            {'number': {'path': ['organizations.Phone1Number', 'organizations.Phone2Number']}} # nested, multiple objects in original input file map to one field in HSDS
        ]
    }
```

and then calling the nested_map function.

Once the collections have been created, we search through each collection, linking parent and child objects together by ID and removing linked child objects from the collection, before outputting the final HSDS objects as JSON files.
