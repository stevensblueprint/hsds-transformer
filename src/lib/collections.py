from pathlib import Path
import re
from .parser import parse_input_csv, parse_nested_mapping, validate_mapping_against_parsed_data
from .mapper import nested_map, get_process_order
from .relationships import identify_parent_relationships
from .logger import transformer_log
from typing import Dict, List, Tuple, Any, Optional

def build_collections(data_directory: str):
    """
    Builds collections by converting rows from input CSVs into nested objects according to their corresponding mapping files.
    
    Requires mapping files named "<input_file_name>_<object_type>_mapping.csv" alongside matching "<input_file_name>.csv" input files. For each valid pair, parses and validates the mapping, applies an optional mapping filter, converts each input row into a nested dictionary, and groups resulting objects by object type. Normalizes certain edge-case object types (e.g., serviceatlocation → service_at_location) and skips missing or empty inputs/mappings.
    
    Parameters:
        data_directory (str): Path to the directory containing input CSVs and mapping CSVs.
    
    Returns:
        List[Tuple[str, List[Dict[str, Any]]]]: A list of (object_type, objects) tuples where `objects` is a list of nested dictionaries produced from the corresponding input CSV.
    
    Raises:
        ValueError: If the input directory is empty, or if no mapping files are found (or no CSV files exist at all).
    """
    transformer_log.section("Build Collections")
    transformer_log.log(f"Input directory: {data_directory}")
    
    data_directory = Path(data_directory) # Converts provided folder path into a Path object
    
    if not any(data_directory.iterdir()):
        raise ValueError(f"Input directory '{data_directory}' is empty.")

    results = [] # List of tuples like ("organization", [dict_list])
    
    mapping_files = list(data_directory.glob("*_mapping.csv"))
    transformer_log.log(f"Found {len(mapping_files)} mapping file(s)")
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

        # Edge case where service_at_location has a key for both a child and parent
        if object_type.lower() in ("serviceatlocation", "servicesatlocation"):
            object_type = "service_at_location"

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

        validate_mapping_against_parsed_data(
            mapping_spec=mapping,
            input_rows=input_rows,
            filename=input_name,
            mapping_file=mapping_file.name,
        )

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
        transformer_log.log(f"  {object_type}: {len(objects)} object(s) from {input_file.name}")

    # Summary of build_collections
    total_objects = sum(len(objs) for _, objs in results)
    transformer_log.log(f"Total collections built: {len(results)}")
    transformer_log.log(f"Total objects created: {total_objects}")
    
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
    Embed an original object into matching target objects across collections using provided relation tuples.
    
    Each relation is a (target_collection, target_id) pair; the function finds the target object in collection_map by id_field and attaches original to it in one of three ways:
    - If original_type == "service_at_location", appends original to the target under the key "service_at_location" (as a list).
    - If (target_collection, original_type) is in SINGULAR_CHILD_CASES, sets target[original_type] = original (singular embed).
    - Otherwise, appends original to an existing list field on the target (preferring a singular key if it already holds a list), or creates a pluralized list key and appends there. Pluralization uses English rules: add "es" for endings in "s", "sh", "ch", "x", "z"; otherwise add "s".
    
    Parameters:
        collection_map (Dict[str, List[Dict[str, Any]]]): Mapping from collection names to lists of objects to search and modify.
        original_type (str): Type name of the original object (used to choose which target field to populate).
        original (Dict[str, Any]): The object to embed into matching targets (may be mutated if reverse relationships are created).
        relations (List[Tuple[str, str]]): List of (collection_name, id) tuples identifying targets to attach to; empty list causes no action.
        id_field (str, optional): Field name used to match target_id against target objects' identifiers. Defaults to "id".
    
    Side effects:
        Mutates objects in collection_map (and possibly the original object) in-place; does not return a value.
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

        # Edge case where service_at_location has a key for both a child and parent
        if original_type == "service_at_location":
            append_to_list_field(target, "service_at_location", original)
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



def searching_and_assigning(collections: List[Tuple[str, List[Dict[str, Any]]]]) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """
    Link child objects into their parent targets based on inferred relationships and return the cleaned collections in processing order.
    
    Parameters:
        collections (List[Tuple[str, List[Dict[str, Any]]]]): A list of (collection_name, objects) pairs where each objects value is a list of dictionaries representing items in that collection. Item dictionaries may contain fields (e.g., `<parent>_id`) used to infer parent relationships.
    
    Returns:
        List[Tuple[str, List[Dict[str, Any]]]]: A list of (collection_name, objects) pairs in the determined processing order. Child objects that were embedded into parent objects are removed from their original top-level collections; embedded objects appear only inside their parent targets in the returned structure.
    """
    transformer_log.section("Searching and Assigning")
    
    if not collections:
        transformer_log.log("No collections to process")
        return collections

    # Build collection_map once and reuse it everywhere
    # Converts the list of tuples into a dict for faster lookup
    collection_map = {}
    for name, objs in collections:
        collection_map[name] = objs # Tuple structure: ("organization", [dicts]) is now a key value pair

    # Log counts before processing
    transformer_log.log("Object counts before linking:")
    for name, objs in collections:
        transformer_log.log(f"  {name}: {len(objs)}")

    # Correct order to process object types
    process_order = get_process_order(collections)
    transformer_log.log(f"Process order: {' -> '.join(process_order)}")

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

    # Rebuilds the final result as a list of tuples to match the original format returned in build_collections
    final_result = []
    for name in process_order:
        # Only includes collection in map
        if name in collection_map:
            objects = collection_map.get(name, []) # Gets cleaned list of objects
            final_result.append((name, objects)) # Adds it back as (name, objects) tuple

    # Log counts after linking and cleanup
    transformer_log.log("Object counts after linking:")
    total_remaining = 0
    for name, objs in final_result:
        transformer_log.log(f"  {name}: {len(objs)}")
        total_remaining += len(objs)
    
    # Log how many were embedded
    total_deleted = sum(len(objs) for objs in to_delete.values())
    transformer_log.log(f"Objects embedded into parents: {total_deleted}")
    transformer_log.log(f"Total top-level objects remaining: {total_remaining}")

    return final_result