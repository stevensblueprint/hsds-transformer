from pathlib import Path
import re
from .parser import parse_input_csv, parse_nested_mapping
from .mapper import nested_map, get_process_order
from .relationships import identify_parent_relationships
from .relations import HSDS_RELATIONS
from typing import Dict, List, Tuple, Any, Optional
from uuid import UUID, uuid5

# TODO: Initialize UUID with a proper fixed value
NAMESPACE = UUID("{12345678-1234-5678-1234-567812345678}")

# Global counter for hsds-object ID generation
_id_counter = 0


def build_collections(data_directory: str):
    """
    From multiple mapping and input CSV files, returns a list of tuples like: [("organization", [dicts]), ("location", [dicts]), ...]
    Each mapping file name MUST follow this format: "<input_file_name>_<object_type>_mapping.csv
    This function pairs each input CSV with its correspodning mapping file and converts flat CSV rows into nested dictionaries
    """

    data_directory = Path(data_directory) # Converts provided folder path into a Path object
    
    if not any(data_directory.iterdir()):
        raise ValueError(f"Input directory '{data_directory}' is empty.")

    results = [] # List of tuples like ("organization", [dict_list])

    mapping_files = list(data_directory.glob("*_mapping.csv"))
    if not mapping_files:
        # Check if there are any CSVs at all to give a better error message
        csv_files = list(data_directory.glob("*.csv"))
        if not csv_files:
            raise ValueError(f"No CSV files found in '{data_directory}'.")
        else:
            raise ValueError(f"No mapping files (*_mapping.csv) found in '{data_directory}'.")

    # Goes through every CSV file in the folder that ends with "_mapping.csv"
    for mapping_file in mapping_files:
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
        
        if not input_rows:
            print(f"Warning: Input file '{input_file.name}' is empty or has no valid rows. Skipping.")
            continue

        # Parses the mapping file into a nested structure and optional filter
        mapping, filter_spec = parse_nested_mapping(str(mapping_file), input_name)

        if not mapping:
            print(f"Warning: Mapping file '{mapping_file.name}' is empty or invalid. Skipping.")
            continue

        objects = [] # Converted object list

        # Build a glom path-based filter for nested_map, if it was provided
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

        results.append((object_type, objects)) # Adds tuple of object type and list of dictionaries. For example: ("organization", [{x}, {y}, ...])

    return results


SINGULAR_CHILD_CASES = { # (target_collection, original_type)
    ("service", "organization"),
    ("service", "program"),
    ("service_at_location", "location"),
    ("attribute", "taxonomy_term"),
    ("taxonomy_term", "taxonomy_detail"),
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
    collection_map: Dict[str, List[Dict[str, Any]]],
    original_type: str,
    original: Dict[str, Any],
    relations: List[Tuple[str, str]],
    *,
    id_field: str = "id",
) -> None:
    """
    Attaches "original" to matching targets in collection_map based on relations
    Params: 
    collection_map -> dict[str, [dict]]
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
        if original_type.endswith(("s", "sh", "ch", "x", "z")):
            list_key_candidates = [original_type, f"{original_type}es"]
        else:
            list_key_candidates = [original_type, f"{original_type}s"]

        appended = False
        for candidate_key in list_key_candidates:
            if isinstance(target.get(candidate_key), list):
                append_to_list_field(target, candidate_key, original)
                appended = True
                break

        if not appended:
            plural_key = original_type # Adds base word
            # Adds s or es based on english plural ending rules
            if original_type.endswith(("s", "sh", "ch", "x", "z")):
                plural_key += "es"
            else:
                plural_key += "s"

            # Reverse relationship where parent holds child ID check
            if (target_collection, original_type) in SINGULAR_CHILD_CASES:
                append_to_list_field(original, target_collection, target)
            else:
                append_to_list_field(target, plural_key, original)


def generate_ids(data: Any, requestor_identifier: Optional[str] = None, visited: Optional[set] = None) -> None:
    """
    Recursively traverses the data structure (list or dict) to generate IDs for objects.

    If an object (dict) doesn't have an ID, it generates one using UUID-5.
    If an object already has an ID, it moves the old ID to a child attribute object
    with label "Previous ID" and generates a new ID.

    Args:
        data: The data structure to process (list of dicts, or a single dict).
        requestor_identifier: Optional identifier for UUID generation.
        visited: Set tracking visited objects to prevent re-processing shared references.
    """
    if visited is None:
        visited = set()

    if isinstance(data, list):
        for item in data:
            generate_ids(item, requestor_identifier, visited)
    elif isinstance(data, dict):
        # Skip if this dict has already been processed
        obj_id = id(data)
        if obj_id in visited:
            return
        visited.add(obj_id)

        # Recursively process all values in the dictionary FIRST
        for key, value in list(data.items()):
            # Skip processing the 'id' field itself
            if key != "id":
                generate_ids(value, requestor_identifier, visited)

        # Process this object's ID
        # Check if ID exists
        global _id_counter
        if "id" in data:
            old_id = data["id"]
            # Build string for UUID5 based on presence of requestor_identifier and old_id
            if requestor_identifier:
                string_for_uuid = (
                    f"hsds-object-{requestor_identifier}-{old_id}-{_id_counter}"
                )
            else:
                string_for_uuid = f"hsds-object-{old_id}-{_id_counter}"
            data["id"] = str(uuid5(NAMESPACE, string_for_uuid))
            _id_counter += 1
        else:
            # No ID exists, generate one
            if requestor_identifier:
                string_for_uuid = f"hsds-object-{requestor_identifier}-{_id_counter}"
            else:
                string_for_uuid = f"hsds-object-{_id_counter}"
            data["id"] = str(uuid5(NAMESPACE, string_for_uuid))
            _id_counter += 1


# Remove legacy *_id fields from all objects after linking
def remove_legacy_id_fields(obj):
    if isinstance(obj, list):
        for item in obj:
            remove_legacy_id_fields(item)
    elif isinstance(obj, dict):
        keys_to_remove = []
        for k in obj.keys():
            if k.endswith("_id"):
                base_name = k[:-3]
                if base_name in HSDS_RELATIONS:
                    keys_to_remove.append(k)
        for k in keys_to_remove:
            del obj[k]
        for v in obj.values():
            remove_legacy_id_fields(v)


def searching_and_assigning(
    collections: List[Tuple[str, List[Dict[str, Any]]]],
    requestor_identifier: Optional[str] = None,
) -> List[Tuple[str, List[Dict[str, Any]]]]:
    if not collections:
        return collections

    # Build collection_map once and reuse it everywhere
    # Converts the list of tuples into a dict for faster lookup
    collection_map = {}
    for name, objs in collections:
        collection_map[name] = objs # Tuple structure: ("organization", [dicts]) is now a key value pair

    # Correct order to process object types
    process_order = get_process_order(collections)

    # Creates a list to track which objects should be deleted
    to_delete = {}
    for name, _ in collections:
        to_delete[name] = [] # Each collection starts with a empty list

    # Iterates through each object type in the correct order
    for obj_type in process_order:
        objects = collection_map.get(obj_type) # Retrieves all objs (dicts) of this type from the mapping
        if not objects: # If no objects, skip to next
            continue
        
        # Loops through each object in collection
        for original in list(objects):
            relations = identify_parent_relationships(original) # Dynamically infers relations from *_id fields
            if not relations: # If object has no relation, skip it
                continue

            # Pass collection_map directly instead of the full collections list
            attach_original_to_targets(collection_map, obj_type, original, relations)

            # Checks to see if object was linked after attached
            for target_collection, target_id in relations:
                found = find_in_collection(collection_map, target_collection, target_id, "id") # Looks for target in collection
                if found: # Once confirmed attached, stops checking relations
                    to_delete[obj_type].append(original) # Adds to be deleted later
                    break
    
    # Goes through each collection type and removes objs that were attached
    for c_name, objs_to_remove in to_delete.items():
        updated_objects = [] # New list exluding deleted items
        for o in collection_map[c_name]:
            if o not in objs_to_remove:
                updated_objects.append(o)
        collection_map[c_name] = updated_objects # Replaces old list with updated list

    for name, objects in collection_map.items():
        remove_legacy_id_fields(objects)
        generate_ids(objects, requestor_identifier)

    # Rebuilds the final result as a list of tuples to match the original format returned in build_collections
    final_result = []
    for name in process_order:
        # Only includes collection in map
        if name in collection_map:
            objects = collection_map.get(name, []) # Gets cleaned list of objects
            final_result.append((name, objects)) # Adds it back as (name, objects) tuple

    return final_result
