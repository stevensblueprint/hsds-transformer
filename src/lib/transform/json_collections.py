import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .parser import validate_mapping_against_parsed_data
from .mapper import nested_map
from .logger import transformer_log


def parse_input_json(input_file: str, filename: str) -> list[dict]:
    """
    Reads a JSON file containing an array of record objects and returns them
    in the same shape that parse_input_csv() produces:
    [{"filename": {"field": "value"}}, ...]

    Raises ValueError if the file is not valid JSON or not a top-level array.
    """
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in '{input_file}': {e}")

    if not isinstance(data, list):
        raise ValueError(
            f"JSON source file '{input_file}' must contain a top-level array of records, "
            f"got {type(data).__name__}."
        )

    rows = []
    for record in data:
        if not isinstance(record, dict):
            continue
        # Flatten values to strings to match CSV behavior where all values are strings
        normalized = {}
        for k, v in record.items():
            key = k.strip() if isinstance(k, str) else k
            if isinstance(v, str):
                normalized[key] = v
            elif v is None:
                normalized[key] = ""
            else:
                normalized[key] = str(v)
        rows.append({filename: normalized})

    return rows


def parse_json_mapping(mapping_file: str, filename: str) -> tuple[dict, dict | None]:
    """
    Reads a JSON mapping file and converts it into the same (mapping_spec, filter_spec)
    tuple that parse_nested_mapping() returns.

    Expected format:
    {
      "filter": {"column": "col_name", "value": "match_value"},   // optional
      "mappings": [
        {"output_path": "id", "input_path": "id"},
        {"output_path": "phones[].number", "input_path": "phone1;phone2", "split": ",", "strip": "<>"}
      ]
    }

    Raises ValueError for structural problems.
    """
    try:
        with open(mapping_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in mapping file '{mapping_file}': {e}")

    if not isinstance(raw, dict):
        raise ValueError(
            f"Mapping file '{mapping_file}' must contain a JSON object, "
            f"got {type(raw).__name__}."
        )

    if "mappings" not in raw:
        raise ValueError(f"Mapping file '{mapping_file}' is missing required 'mappings' key.")

    mappings_list = raw["mappings"]
    if not isinstance(mappings_list, list) or len(mappings_list) == 0:
        raise ValueError(f"Mapping file '{mapping_file}' has empty or invalid 'mappings' array.")

    # Parse optional filter
    filter_spec = None
    filter_raw = raw.get("filter")
    if isinstance(filter_raw, dict):
        col = (filter_raw.get("column") or "").strip()
        val = (filter_raw.get("value") or "").strip()
        if col and val:
            filter_spec = {"column": col, "value": val}

    # Build the nested mapping_spec dict, same structure as parse_nested_mapping() output
    mapping: dict = {}

    for i, entry in enumerate(mappings_list):
        if not isinstance(entry, dict):
            raise ValueError(
                f"Mapping file '{mapping_file}': entry {i} must be an object."
            )

        output_path = (entry.get("output_path") or "").strip()
        input_path = (entry.get("input_path") or "").strip()

        if not output_path or not input_path:
            raise ValueError(
                f"Mapping file '{mapping_file}': entry {i} is missing "
                f"'output_path' or 'input_path'."
            )

        split_val = (entry.get("split") or "").strip()
        strip_val = (entry.get("strip") or "").strip()
        transform_val = (entry.get("transform") or "").strip()

        # Handle semicolon-separated input fields (same as CSV path)
        input_fields = [field.strip() for field in input_path.split(";") if field.strip()]

        if len(input_fields) > 1:
            paths = [f"{filename}.{field}" for field in input_fields]
            path_value = {"path": paths}
        else:
            path_value = {"path": f"{filename}.{input_fields[0]}"}

        # Build the leaf mapping object
        map_obj = path_value.copy()
        if split_val:
            map_obj["split"] = split_val
        if strip_val:
            map_obj["strip"] = strip_val
        if transform_val:
            map_obj["transform"] = transform_val

        # Walk the output_path to build nested structure (identical to parse_nested_mapping logic)
        parts = output_path.split(".")
        current_level = mapping

        for j, part in enumerate(parts):
            is_last = j == len(parts) - 1

            if part.endswith("[]"):
                key = part[:-2]
                if is_last:
                    current_level[key] = [map_obj]
                else:
                    if key not in current_level:
                        current_level[key] = [{}]
                    current_level = current_level[key][0]
            else:
                key = part
                if is_last:
                    current_level[key] = map_obj
                else:
                    current_level = current_level.setdefault(key, {})

    return mapping, filter_spec


def build_collections_from_json(data_directory: str) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """
    JSON counterpart to build_collections(). Discovers *_mapping.json files,
    pairs them with <input_name>.json source files, validates, transforms,
    and returns the same [(object_type, [dicts])] structure.

    Returns an empty list if no JSON mapping files are found (not an error).
    Raises ValueError for validation failures.
    """
    data_directory = Path(data_directory)
    results: List[Tuple[str, List[Dict[str, Any]]]] = []

    json_mapping_files = list(data_directory.glob("*_mapping.json"))
    if not json_mapping_files:
        return results

    transformer_log.section("Build Collections (JSON)")
    transformer_log.log(f"Input directory: {data_directory}")
    transformer_log.log(f"Found {len(json_mapping_files)} JSON mapping file(s)")

    for mapping_file in json_mapping_files:
        match = re.match(r"(.+)_([A-Za-z0-9]+)_mapping\.json", mapping_file.name)
        if not match:
            continue

        input_name, object_type = match.groups()

        if object_type.lower() in ("serviceatlocation", "servicesatlocation"):
            object_type = "service_at_location"

        input_file = data_directory / f"{input_name}.json"
        if not input_file.exists():
            continue

        input_rows = parse_input_json(str(input_file), input_name)

        if not input_rows:
            print(f"Warning: JSON input file '{input_file.name}' is empty or has no valid records. Skipping.")
            continue

        mapping, filter_spec = parse_json_mapping(str(mapping_file), input_name)

        if not mapping:
            print(f"Warning: JSON mapping file '{mapping_file.name}' is empty or invalid. Skipping.")
            continue

        validate_mapping_against_parsed_data(
            mapping_spec=mapping,
            input_rows=input_rows,
            filename=input_name,
            mapping_file=mapping_file.name,
            input_extension="json",
        )

        objects = []

        nested_map_filter = None
        if filter_spec is not None:
            column_name = filter_spec.get("column")
            match_value = filter_spec.get("value")
            if column_name and match_value is not None:
                nested_map_filter = {"path": f"{input_name}.{column_name}", "value": match_value}

        for row in input_rows:
            mapped_dictionary = nested_map(row, mapping, filter_spec=nested_map_filter)
            if mapped_dictionary is not None:
                objects.append(mapped_dictionary)

        results.append((object_type, objects))
        transformer_log.log(f"  {object_type}: {len(objects)} object(s) from {input_file.name}")

    if results:
        total_objects = sum(len(objs) for _, objs in results)
        transformer_log.log(f"Total JSON collections built: {len(results)}")
        transformer_log.log(f"Total JSON objects created: {total_objects}")

    return results
