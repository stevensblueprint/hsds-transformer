import csv
import os
from pathlib import Path
from typing import Set, Any, Dict

def parse_input_csv(input_file, filename) -> list:
    """
    Takes a csv file and return a list of dictionaries of the form: 
    [{"organization" : { "columns": "value"}}], where every dictionary is a row
    """
    with open(input_file, mode='r', newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        
        filename = os.path.splitext(os.path.basename(input_file))[0]

        input = []
        for row in reader:
            # Normalize header keys by trimming whitespace
            normalized = { (k.strip() if isinstance(k, str) else k): v for k, v in row.items() }
            input.append({filename: normalized})

    return input

def parse_nested_mapping(mapping_file, filename) -> tuple[dict, dict | None]:
    """
    Takes a mapping CSV file with the following structure and returns a tuple
    of (mapping_dict, filter_spec or None):

    - Row 1: Column headers (ignored by position-based parsing)
    - Row 2: Optional filter row: [column_name_to_check, value_to_match]
             If empty, no filter is applied (returns None for filter)
    - Row 3+: Mapping rows: [output_path, input_field]
    """

    mapping: dict = {}
    filter_spec: dict | None = None

    with open(mapping_file, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)

        # Row 1: header
        try:
            next(reader) # Skip header row
        except StopIteration:
            return mapping, None

        # Row 2: optional filter row
        try:
            filter_row = next(reader)
        except StopIteration:
            filter_row = None

        if filter_row and len(filter_row) >= 2:
            filter_column = (filter_row[0] or '').strip()
            filter_value = (filter_row[1] or '').strip()
            if filter_column and filter_value:
                # organize filter column and value into dictionary
                filter_spec = {"column": filter_column, "value": filter_value}

        # Row 3+: mapping rows
        for row in reader:
            if not row or len(row) < 2:
                continue

            # First column is the desired output path, e.g. "locations[].address"
            path = (row[0] or '').strip()
            # Second column is the field from the input file, e.g. "address"
            input_field = (row[1] or '').strip()
            split_val = (row[2] or '').strip() if len(row) > 2 else ""
            strip_val = (row[3] or '').strip() if len(row) > 3 else ""

            # Skip the row if the path or input field is empty
            if not path or not input_field: 
                continue
        
            # Check if input_field contains multiple fields separated by semicolons
            input_fields = [field.strip() for field in input_field.split(';') if field.strip()]
            
            # Create path(s) - list if multiple fields, single string if one field
            if len(input_fields) > 1:
                # Multiple fields: create list of paths
                paths = [f"{filename}.{field}" for field in input_fields]
                path_value = {"path": paths}
            else:
                # Single field: keep as string path (backward compatible)
                path_value = {"path": f"{filename}.{input_fields[0]}"}

            # Build the mapping object we'll attach at the leaf
            map_obj = path_value.copy()
            if split_val:
                map_obj["split"] = split_val
            if strip_val:
                map_obj["strip"] = strip_val

            # Split the path into parts
            parts = path.split('.')
            current_level = mapping # Start with top level of output dictionary

            # Loop through each part of the path to create the nested structure
            for i, part in enumerate(parts):
                is_last = (i == len(parts) - 1)

                # Case A: The path part indicates a list through "[]"
                if part.endswith('[]'):
                    key = part[:-2] # Remove the "[]" to get the key name
                    
                    # If this is the last part, store a list whose single element is the leaf mapping
                    if is_last:
                        current_level[key] = [map_obj]
                    else:
                        # Initialize the list if it doesn't exist
                        if key not in current_level:
                            current_level[key] = [{}]

                    # Move the pointer of the dictionary inside the list
                    current_level = current_level[key][0]
                
                # Case B: The path part is a standard dictionary key
                else:
                    key = part

                    # Set the final value if it's the last part of the path
                    if is_last:
                        current_level[key] = map_obj

                    # Go one level deeper if it's not the last part of the path
                    else:
                        current_level = current_level.setdefault(key, {})

    return mapping, filter_spec


def parse_mapping(mapping_file, filename) -> dict:
    """
    Parses a flat mapping. Not currently used in the transformer.
    Takes a mapping csv file and return a dictionary of the form: 
    [{"output_field": {"path": "filename.original_field}}]
    """
    with open(mapping_file, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)

        next(reader)
        
        mapping = {}
        for row in reader:
            if row[2]:
                mapping[row[1]] = {"path": filename + "." + row[0], "split": row[2]}
            else:
                mapping[row[1]] = {"path": filename + "." + row[0]}

    return mapping

def validate_mapping_against_parsed_data(
    mapping_spec: Dict[str, Any],
    input_rows: list[dict],
    filename: str,
    mapping_file: str,
) -> None:
    """
    Check that every column referenced in a mapping exists in the original file
    This uses already parsed data instead of reopening CSVs
    """

    if not input_rows:
        # Base case
        return

    # Gets the first row to use as a structure example
    first_row = input_rows[0]

    # checks if row follows structuere: { filename: {column: value, ... } }
    # If it does, it pulls out its inner column dict
    if isinstance(first_row, dict) and filename in first_row and isinstance(first_row[filename], dict):
        data_row = first_row[filename]
    else:
        # if not it treats the row as the set of columns itself
        data_row = first_row

    original_fields = {str(k).strip() for k in data_row.keys() if str(k).strip()}

    referenced_cols: set[str] = set()

    def walk(node: Any) -> None:
        # Recursively "walk" through the mapping and pick out any path fields
        if isinstance(node, dict):
            if "path" in node:
                p = node["path"]
                if isinstance(p, str):
                    paths = [p]
                elif isinstance(p, list):
                    paths = [x for x in p if isinstance(x, str)]
                else:
                    paths = []

                for full in paths:
                    # We only care about paths relevant to this file (ex: "AgencyMapping.Agency")
                    prefix = f"{filename}."
                    if full.startswith(prefix):
                        col = full[len(prefix):]
                        if col:
                            referenced_cols.add(col.strip())
            # Recursively run in children
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(mapping_spec)

    missing = sorted(col for col in referenced_cols if col not in original_fields)

    if missing:
        # Finds any columns that the mapping wants that aren't in the file
        missing_str = ", ".join(missing)
        raise ValueError(f"Invalid mapping: these columns are referenced in '{mapping_file}' for input '{filename}.csv' but do not exist in the input data: {missing_str}")