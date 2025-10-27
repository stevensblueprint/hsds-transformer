# HSDS Transformer
## Setup
Create a virtualenv
```bash
python3 -m venv .venv
```

Activate the virtualenv
```bash
source .venv/bin/activate
```

Install dependencies
```bash
pip3 install -r requirements.txt
```

## Running the command line tool
**Currently works for transforming a csv into an organization object with no nested fields and only outputs the object created from the first row.**

Add the csv file to be transformed into the data folder.

Create and add a mapping csv file to the data folder with two columns: the left column with the column names in the file to be transformed and the right column with paths to the associated field in the goal object. See mapping.csv in data for an example.

Make sure you're in the root folder.

Finally run, `python -m src.cli.main path\to\input.csv path\to\mapping.csv` where the two paths are relative paths to the input file and mapping file respectively. (Using example csvs: `python -m src.cli.main data\HSD_provider.csv data\mapping.csv`).

## Generating IDs
We can also generate IDs (specifically UUID-5) for objects without IDs.
1. Make a copy of the `.env.example` file in the root directory and rename your copy `.env`.
2. Replace the fixed-value and the identifier string with your own.
3. Run the transformer as normal.
Without the `.env` file, the transformer will not run ID generation.

## Notes: 

We parse the input file into the form:
```
src = {
        "organization": {
            "entity_id": "org-123",
            "entity_name": "Acme Corp",
            "entity_description": "A fictional company",
        }
    }
```

and the mapping file into the form:
```
mapping = {
        "id": {"path": "organization.entity_id"},
        "name": {"path": "organization.entity_name"},
        "description": {"path": "organization.entity_description"},
    }
```
and then call the map() function.

## Running the api
```bash
uvicorn api.app:app --app-dir src --reload
```