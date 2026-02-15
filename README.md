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

**Transforms CSVs into HSDS-compliant objects given proper associated mapping.**

Move the csv files to be transformed with their associated mapping (csv) files into a directory (if you're testing in this repository, create a folder for your files in the data folder). See the current `data` folder for examples.

Make sure you're in the root folder.

```bash
# macOS/Linux (bash/zsh)
# Transform CSVs to HSDS JSON
python3 -m src.cli.main path/to/datadir
python3 -m src.cli.main path/to/datadir -o path/to/outputdir
```

```bash
# Windows (PowerShell/cmd)
# Transform CSVs to HSDS JSON
python -m src.cli.main path\to\datadir
python -m src.cli.main path\to\datadir -o path\to\outputdir
```

Without specifying an output directory, the transformer will create one in your root directory or add the files to `output` if it already exists.

**Reverse transform (HSDS JSON to CSV inputs).**
_NOTE Currently the actual reverse transformation is not implemented_

```bash
# macOS/Linux (bash/zsh)
python3 -m src.cli.reverse_transform --mapping-dir path/to/mappings --hsds-dir path/to/hsds-json --output-dir path/to/output
```

```bash
# Windows (PowerShell/cmd)
python -m src.cli.reverse_transform --mapping-dir path\to\mappings --hsds-dir path\to\hsds-json --output-dir path\to\output
```

The output directory is optional and defaults to `reverse_output`.

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

## Running the api

```bash
# All Platforms
# Start the FastAPI server
uvicorn api.app:app --app-dir src --reload
```
