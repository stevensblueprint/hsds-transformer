from pathlib import Path
import re
from .parser import parse_input_csv, parse_nested_mapping
from .mapper import nested_map
from typing import Dict, List, Tuple, Any, Optional

def build_collections(data_directory: str):
    """
    From multiple mapping and input CSV files, returns a list of tuples like: [("organization", [dicts]), ("location", [dicts]), ...]
    Each mapping file name MUST follow this format: "<input_file_name>_<object_type>_mapping.csv
    This function pairs each input CSV with its correspodning mapping file and converts flat CSV rows into nested dictionaries
    """
    
    data_directory = Path(data_directory) # Converts provided folder path into a Path object
    results = [] # List of tuples like ("organization", [dict_list])

    # Goes through every CSV file in the folder that ends with "_mapping.csv"
    for mapping_file in data_directory.glob("*_mapping.csv"):
        match = re.match(r"(.+)_([A-Za-z0-9]+)_mapping\.csv", mapping_file.name) # Parses and extracts name before "_mapping" using regex
        
        # Skips files with no _mapping ending
        if not match:
            continue

        input_name, object_type = match.groups() # Grabs the name and type of object for labeling in results
        input_file = data_directory / f"{input_name}.csv" # Uses the extracted name to find the corresponding input CSV file

        # Skips this mapping if the matching input CSV doesn't exist
        if not input_file.exists():
            continue
        
        # Parses through input CSV rows and returns something like [{"organizations": {"id": "1", "name": "Blueprint"}}, ...]
        input_rows = parse_input_csv(str(input_file), input_name)

        # Parses the mapping file into a nested structure 
        mapping = parse_nested_mapping(str(mapping_file), input_name)

        objects = [] # Converted object list

        for row in input_rows:
            mapped_dictionary = nested_map(row, mapping) # Maps to transform flat CSV into nested dictionary
            objects.append(mapped_dictionary)

        results.append((object_type, objects)) # Adds tuple of object type and list of dictionaries. For example: ("organization", [{x}, {y}, ...])

    return results


SINGULAR_CHILD_CASES = {
    ("service", "organization"),  # (target_collection, original_type)
}


def find_in_collection(
    collection_map: Dict[str, List[Dict[str, Any]]],
    collection_name: str,
    target_id: str,
    id_field: str,
) -> Optional[Dict[str, Any]]:
    """
    Linear search for the dict in the given collection that has id == target_id
    Skips dictionaries with no id key
    Returns the found dict or None
    """
    items = collection_map.get(collection_name)
    if not items:
        return None

    for d in items:
        if id_field not in d:
            # Missing id: skip (move on to next dict)
            continue
        if isinstance(d[id_field], str) and d[id_field] == target_id:
            return d

    return None


def append_to_list_field(
    target: Dict[str, Any],
    key: str,
    value: Dict[str, Any],
) -> None:
    """
    Append value to target[key] if it exists and is a list
    Otherwise create target[key] as a new list containing value
    """
    existing = target.get(key)
    if isinstance(existing, list):
        existing.append(value)
    else:
        target[key] = [value]


def attach_original_to_targets(
    collections: List[Tuple[str, List[Dict[str, Any]]]],
    original_type: str,
    original: Dict[str, Any],
    relations: List[Tuple[str, str]],
    *,
    id_field: str = "id",
) -> None:
    """
    Attaches "original" to matching targets in collections based on relations
    Params: 
    collections -> list[(str, [dict])] 
    original_type -> str
    original -> dict (the dictionary to embed into matching targets)
    relations -> list[(str, str)] (tuples of (collection_name, id) to search for. If empty: skip)
    id_field -> str (field used as identifier)

    Looks through the specified collections for objects with the given IDs and attaches the original dictionary to them
    Most links are stored as lists, except for the special case where a service has one Organization
    Skips anything missing an ID or a match
    """

    # If there are no relations to process, return
    if not relations:
        return

    # Lookup from a collection name to a list of dictionaries
    collection_map: Dict[str, List[Dict[str, Any]]] = {
        name: items for name, items in collections
    }

    for target_collection, target_id in relations:
        # Skips empty/invalid ids
        if not target_id:
            continue

        target = find_in_collection(
            collection_map=collection_map,
            collection_name=target_collection,
            target_id=target_id,
            id_field=id_field,
        )
        if target is None:
            # Skips if no corresponding dict
            continue

        # SINGULAR EMBED CASE (HARD CODED)
        if (target_collection, original_type) in SINGULAR_CHILD_CASES:
            target[original_type] = original
            continue

        # By default we link using a list
        # First check if theres already a list under the singular key (e.g. "location")
        # If not try the plural form (+s)
        # If not, creates a new list
        list_key_candidates = [original_type, f"{original_type}s"]

        appended = False
        for candidate_key in list_key_candidates:
            if isinstance(target.get(candidate_key), list):
                append_to_list_field(target, candidate_key, original)
                appended = True
                break

        if not appended:
            plural_key = f"{original_type}s"
            append_to_list_field(target, plural_key, original)
