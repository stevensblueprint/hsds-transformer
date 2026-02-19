# HSDS Transformer: Project Context

This document provides essential context and instructions for the HSDS Transformer project.

## Project Overview

The **HSDS Transformer** is a Python-based utility designed to convert custom CSV datasets into JSON files compliant with the [Human Services Data Specification (HSDS)](https://hsds.foundation/). It features a flexible mapping system that allows users to define how flat CSV data should be nested and linked to form complex HSDS objects (e.g., Organizations, Services, Locations).

### Key Technologies
- **Python 3.13+**: Core programming language.
- **Glom**: Used for deep data transformation and path-based extraction.
- **Click**: Powers the Command Line Interface (CLI).
- **FastAPI & Uvicorn**: Provides a web API for remote transformation.
- **UV**: Recommended package and environment manager.

## Architecture & Core Logic

1. **Parsing (`src/lib/parser.py`)**: Reads input CSVs and their associated mapping CSVs. Mapping files must follow the naming convention `<input_name>_<object_type>_mapping.csv`.
2. **Mapping (`src/lib/mapper.py`)**: The `nested_map` function uses `glom` and the mapping specification to transform flat rows into nested dictionaries. It handles complex cases like splits, strips, and index-aligned arrays.
3. **Collection Management (`src/lib/collections.py`)**:
    - `build_collections`: Pairs CSVs with mappings and performs initial transformation.
    - `searching_and_assigning`: Implements the "Link and Cleanup" logic. It identifies parent-child relationships (e.g., a Service belonging to an Organization) and embeds child objects into their parents, removing them from the top-level collection.
4. **Outputs (`src/lib/outputs.py`)**: Saves the final linked HSDS collections as JSON files.

## Building and Running

### Environment Setup
The project uses `uv` for dependency management.

```bash
# Install dependencies (All Platforms)
uv sync
```

### CLI Usage
**Transform CSVs to HSDS JSON:**

```bash
# macOS/Linux (bash/zsh)
python3 -m src.cli.main path/to/datadir [-o path/to/outputdir]

# Windows (PowerShell/cmd)
python -m src.cli.main path\to\datadir [-o path\to\outputdir]
```

- `<data_directory>`: Should contain your input CSVs and their mapping CSVs.
- `-o`: Optional output directory (defaults to `output`).

**Reverse Transform (WIP):**

```bash
# macOS/Linux (bash/zsh)
python3 -m src.cli.reverse_transform --mapping-dir <mapping_dir> --hsds-dir <hsds_json_dir>

# Windows (PowerShell/cmd)
python -m src.cli.reverse_transform --mapping-dir <mapping_dir> --hsds-dir <hsds_json_dir>
```

### API Usage
```bash
# All Platforms
# Start the FastAPI server
uvicorn api.app:app --app-dir src --reload
```
- Endpoint: `POST /transform` accepts a `.zip` file containing CSVs and mappings and returns a `.zip` of HSDS JSON files.

## Development Conventions

- **Mapping Naming**: Files MUST be named `<input_filename>_<object_type>_mapping.csv`.
- **Mapping Format**:
    - Row 1: Headers (ignored).
    - Row 2: Optional Filter (Column, Value).
    - Row 3+: Mappings (Output Path, Input Field, Split, Strip).
- **Relational Integrity**: The `searching_and_assigning` step relies on the `id` and `<parent_type>_id` fields to link objects.
- **HSDS Relations**: Defined in `src/lib/relations.py` and used to determine the processing order of objects.

## Project Structure
- `src/api/`: FastAPI application, middleware, and logging.
- `src/cli/`: Click commands for the transformer and reverse transformer.
- `src/lib/`: Core library logic (parsing, mapping, relationship handling).
- `data/`: Sample datasets and mappings for various formats (iCarol, VisionLink, etc.).
