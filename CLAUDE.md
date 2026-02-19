# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The HSDS Transformer converts arbitrary CSV datasets into JSON files compliant with the Human Services Data Specification (HSDS) v3.1.2. It uses a flexible mapping system to transform flat CSV rows into nested, linked HSDS objects (Organizations, Services, Locations, etc.).

## Core Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Install dependencies (preferred method)
pip3 install uv
uv sync

# Alternative: install with pip
pip3 install -r requirements.txt
```

### Running the CLI Transformer
```bash
# macOS/Linux (bash/zsh)
# Transform CSVs to HSDS JSON
python3 -m src.cli.main path/to/datadir
python3 -m src.cli.main path/to/datadir -o path/to/outputdir

# Reverse transform (WIP - not fully implemented)
python3 -m src.cli.reverse_transform --mapping-dir path/to/mappings --hsds-dir path/to/hsds-json --output-dir path/to/output
```

```bash
# Windows (PowerShell/cmd)
# Transform CSVs to HSDS JSON
python -m src.cli.main path\to\datadir
python -m src.cli.main path\to\datadir -o path\to\outputdir

# Reverse transform (WIP - not fully implemented)
python -m src.cli.reverse_transform --mapping-dir path\to\mappings --hsds-dir path\to\hsds-json --output-dir path\to\output
```

### Running the API
```bash
# All Platforms
# Start FastAPI server
uvicorn api.app:app --app-dir src --reload

# API endpoint: POST /transform
# Accepts: .zip file with CSVs and mapping files
# Returns: .zip file with HSDS JSON files
```

## Architecture

### Transformation Pipeline

The transformation process follows this sequence:

1. **Parsing** (`src/lib/parser.py`)
   - `parse_input_csv()`: Reads CSV files into list of dicts with structure `[{filename: {column: value}}]`
   - `parse_nested_mapping()`: Parses mapping CSV into nested dict structure + optional filter spec
   - `validate_mapping_against_parsed_data()`: Validates that all referenced columns exist in input data

2. **Mapping** (`src/lib/mapper.py`)
   - `nested_map()`: Core transformation engine using glom library
   - Handles complex cases: splits (comma-separated values), strips (character removal), multiple input fields, array alignment
   - Processes filters to conditionally include/exclude rows
   - Returns nested dictionaries matching HSDS structure

3. **Collection Building** (`src/lib/collections.py`)
   - `build_collections()`: Pairs input CSVs with mapping files, applies `nested_map()` to each row
   - Returns list of tuples: `[("organization", [dicts]), ("service", [dicts]), ...]`

4. **Relationship Linking** (`src/lib/relationships.py` + `src/lib/collections.py`)
   - `identify_parent_relationships()`: Dynamically infers parent-child relationships from `*_id` fields
   - `searching_and_assigning()`: Implements "Link and Cleanup" logic
     - Identifies parent objects using `*_id` fields (e.g., `service_id`, `organization_id`)
     - Embeds child objects into their parents (e.g., phones into organizations)
     - Removes embedded children from top-level collections
     - Processes entities in correct order based on dependency DAG

5. **Output** (`src/lib/outputs.py`)
   - Saves final linked collections as individual JSON files per entity type

### Key Architecture Concepts

**Mapping File Format**: Mapping files must follow naming convention `<input_name>_<object_type>_mapping.csv`

Structure:
- Row 1: Headers (ignored)
- Row 2: Optional filter `[column_name, match_value]`
- Row 3+: Mappings `[output_path, input_field, split_char, strip_chars]`

**Path Syntax**:
- `field` - simple field
- `nested.field` - nested object
- `array[]` - array of objects
- `array[].field` - field within array objects
- Semicolon-separated input fields create multiple paths for array alignment

**HSDS Relations DAG** (`src/lib/relations.py`):
Defines parent-child relationships between HSDS entities. Critical for determining:
- Processing order via `get_process_order()`
- Which entities can be embedded in others
- Dependency resolution during linking phase

**Special Cases**:
- `SINGULAR_CHILD_CASES`: Defines 1:1 relationships (e.g., service→organization, not services→organizations)
- Attributes handling: Creates objects with both `value` and `label` (column name) fields
- Parent index alignment: Ensures nested arrays maintain correct index correspondence

## Project Structure

```
src/
├── api/          # FastAPI application
│   ├── app.py           # Main API with POST /transform endpoint
│   ├── middleware.py    # Logging middleware
│   ├── logger.py        # Logger configuration
│   └── utils.py         # API utilities
├── cli/          # Command-line interfaces
│   ├── main.py          # Transform command
│   └── reverse_transform.py  # Reverse transform (WIP)
└── lib/          # Core transformation logic
    ├── parser.py        # CSV and mapping parsers
    ├── mapper.py        # nested_map() transformation engine
    ├── collections.py   # Collection building and linking
    ├── relationships.py # Parent-child relationship inference
    ├── relations.py     # HSDS entity relationship DAG
    ├── outputs.py       # JSON file generation
    ├── maintenance/     # Utilities for HSDS JSON operations
    └── reverse_transform/  # Reverse transformation (WIP)

data/           # Sample datasets and mappings for testing
```

## Development Guidelines

**Mapping Conventions**:
- Mapping files MUST be named `<input_filename>_<object_type>_mapping.csv`
- Multiple semicolon-separated input fields in mapping create path arrays for alignment
- Array alignment preserves index correspondence across multiple fields (e.g., Phone1Number and Phone1Type align at index 0)

**Relational Integrity**:
- Objects link via `id` and `<parent_type>_id` fields
- The `searching_and_assigning()` step relies on these fields to embed children into parents
- Processing order determined by HSDS_RELATIONS DAG ensures parents exist before children

**ID Generation**:
- Currently uses placeholder UUID generation with `NAMESPACE` constant
- TODO comment indicates need for proper entity-specific identifier strings

**Filter Logic**:
- Filters apply during `nested_map()` to conditionally include rows
- Filter spec: `{"path": "filename.column", "value": "match_value"}`
- Rows not matching filter return None and are excluded from output

**Error Handling**:
- `build_collections()` validates that input CSVs exist for each mapping file
- `validate_mapping_against_parsed_data()` ensures all referenced columns exist
- API returns 422 status for validation errors with detailed messages

## Technologies

- **Python 3.13+**: Requires Python 3.13 or higher
- **glom**: Deep data transformation and path-based extraction
- **Click**: CLI framework
- **FastAPI & Uvicorn**: Web API framework and server
- **uv**: Recommended package and environment manager

## API Details

**POST /transform**:
- Accepts: `multipart/form-data` with zip file containing CSVs and mappings
- Handles nested zip folders (extracts single top-level folder if present)
- Returns: `application/zip` with HSDS JSON files
- Status codes: 201 (success), 422 (validation error)

## Notes

- Reverse transformation (`src/cli/reverse_transform.py`) is work in progress
- No formal test framework currently exists; sample data in `data/` directory serves as test cases
- Recent development has focused on API endpoint and handling of unzipped files
- The project uses position-based CSV parsing (via csv.reader/DictReader) not pandas
