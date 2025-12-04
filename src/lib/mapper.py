from __future__ import annotations
from typing import Any, Callable, Dict, List
from datetime import date
from glom import glom
from uuid import UUID, uuid5
from .relations import HSDS_RELATIONS

# TODO: Initialize UUID with a proper fixed value
NAMESPACE = UUID("{12345678-1234-5678-1234-567812345678}")

"""
NESTED_MAP: deals with layer 1 - essentially moving from a flat spreadsheet/csv into a nested format with potentially
different column/field names.
"""

def nested_map(data: Any, mapping_spec: Dict[str, Any], root_data=None, filter_spec=None) -> dict | list | None:
    """
    Process a mapping specification and transform data using glom
    Fixed to always use the root data for path resolution - so the path doesn't get lost during 
    """
    if not isinstance(data, (dict, list, tuple)):
        """
        Checking to ensure data is the correct type
        """
        try:
            data = vars(data)
        except TypeError:
            raise ValueError(
                "source must be a dict, list, tuple, or object with __dict__"
            )

    if root_data is None:
        root_data = data

    # If a filter is provided, ensure this row matches before processing
    if filter_spec is not None:
        try:
            filter_path = filter_spec.get("path")
            filter_value = filter_spec.get("value")
            if filter_path is not None:
                actual_value = glom(root_data, filter_path, default=None)
                # If path doesn't exist, warn that the filter column might not exist/names might mismatch
                if actual_value is None:
                    print(f"WARNING: Filter path '{filter_path}' returned None. Column may not exist in CSV data or has no value.")
                # Normalize comparison - strip whitespace and convert to string
                actual_str = str(actual_value).strip() if actual_value is not None else ""
                filter_str = str(filter_value).strip() if filter_value is not None else ""
                if actual_str != filter_str:
                    return None
        except Exception as e:
            # If path doesn't exist or glom fails, skip this row and log the error
            print(f"WARNING: Filter failed for path '{filter_path}' with value '{filter_value}': {e}")
            return None
        
    def process_value(value, array_context=False, template=None):
        """
        Recursively processes mapping values to transform flat CSV data into nested structures.
        Handles three main cases: path specs (leaf data extraction), nested objects, and arrays.
        
        Args:
            value: The mapping spec or data value to process (dict, list, or scalar).
            template: The parent key name when processing a leaf path spec with split.
                      Used to wrap split parts in objects (e.g., {name: "part"}).
            array_context: Boolean flag indicating when currently processing inside an 
                           array structure (ex. phones[]), handling multiple path arrays 
                           (ex. phones[].number, phones[].name) by aligning indicies.
        """

        def decode_escape_sequences(s):
            """
            Helper to decode common escape sequences from CSV string representations.
                Args: s: input string containing escape sequence
            """
            escape_map = {
                '\\n': '\n',      # newline
                '\\t': '\t',      # tab
                '\\r': '\r',      # carriage return
                '\\"': '"',       # double quote
                "\\'": "'",       # single quote
                '\\\\': '\\',     # backslash
            }
            for escaped, actual in escape_map.items():
                s = s.replace(escaped, actual)
            return s

        def apply_strip(extracted_val, value):
            """Apply strip characters to a single extracted value if specified."""
            if "strip" in value and value["strip"] and isinstance(extracted_val, str):
                strip_val = value["strip"]
                if isinstance(strip_val, str):
                    strip_chars = []
                    for char in strip_val.split(';'):
                        cleaned_char = char.strip(' ')
                        if cleaned_char:
                            cleaned_char = decode_escape_sequences(cleaned_char)
                            strip_chars.append(cleaned_char)
                else:
                    strip_chars = strip_val
                
                for char_to_strip in strip_chars:
                    extracted_val = extracted_val.replace(char_to_strip, "")
            
            return extracted_val

        # Case 1: Value is a dictionary - could be a path specification or nested object
        if isinstance(value, dict):
            # Case 1A: Dictionary contains a "path" key - this is a path specification for data extraction
            if "path" in value:
                path = value["path"]
                
                # Case 1A-1: Path is a list - multiple input fields (semicolon-separated in mapping file)
                # Example: {"path": ["organizations.Phone1Number", "organizations.Phone2Number"]}
                if isinstance(path, list):
                    # Extract values from all paths in the list, preserving None values for alignment logic
                    extracted_values = []
                    for p in path:
                        try:
                            val = glom(root_data, p, default=None)
                            # Strip characters if specified
                            val = apply_strip(val, value)
                            # Convert empty strings to None for consistent filtering later
                            if val == "" or val is None:
                                val = None
                            extracted_values.append(val)
                        except Exception:
                            # If path extraction fails, store None to maintain index alignment
                            extracted_values.append(None)
                    
                    # Sub-Case 1A-1a: In array context (e.g., processing phones[].number)
                    # Return all values including None to allow proper index-based alignment with other fields
                    # Example: phones[].number and phones[].name need to align by index (0 with 0, 1 with 1)
                    if array_context:
                        return extracted_values
                    # Sub-Case 1A-1b: Not in array context (e.g., processing a regular field with multiple sources)
                    # Filter out None values and return single value if only one exists, list if multiple
                    else:
                        filtered = [v for v in extracted_values if v is not None]
                        return filtered if len(filtered) > 1 else (filtered[0] if filtered else None)
                
                # Case 1A-2: Path is a string - single input field (existing behavior, backward compatible)
                # Example: {"path": "organizations.organization_name"}
                else:
                    # Extract the value from the root data using the glom path
                    extracted_val = glom(root_data, path, default=None)

                    # Strip characters if specified
                    extracted_val = apply_strip(extracted_val, value)
                    
                    # Return None for empty strings to maintain consistency with path array handling
                    if extracted_val == "" or extracted_val is None:
                        return None
                    
                    # Sub-Case 1A-2a: Path spec with split directive (comma-separated or other delimiter)
                    # Example: {"path": "organizations.languages", "split": ","}
                    if "split" in value and value["split"]:
                        split_char = value["split"]
                        if isinstance(extracted_val, str):
                            # Split on delimiter and strip brackets and whitespace
                            parts = [part.strip() for part in extracted_val.split(split_char) if part.strip()]
                            parts = [part.strip('{}') for part in parts]
                            
                            # If template is provided, wrap each part with that key (e.g., [{"name": "English"}, {"name": "Spanish"}])
                            if template:
                                return [{template: part} for part in parts]
                            else:
                                # Otherwise return flat list of strings
                                return parts
                    
                    # Sub-Case 1A-2b: No split directive - return value as-is
                    return extracted_val
            # Case 1B: Dictionary does NOT contain "path" key - this is a nested object structure
            # Example: {"phones": [{"number": {"path": ...}, "name": {"path": ...}}]}
            else:
                items = list(value.items())
                
                # Separate items into two categories:
                # 1. Items with path arrays (multiple semicolon-separated fields)
                # 2. Regular items (single paths or nested structures)
                path_array_items = {}
                regular_items = {}
                
                for k, v in items:
                    # Check if this item has a path array (list of paths from semicolon-separated fields)
                    if isinstance(v, dict) and "path" in v and isinstance(v.get("path"), list):
                        path_array_items[k] = v
                    else:
                        regular_items[k] = v
                
                # Case 1B-1: Object contains one or more path arrays (multiple fields to align)
                # Example: phones[].number and phones[].name both have semicolon-separated fields
                if path_array_items:
                    # Get all path lists and determine maximum length for alignment
                    # This ensures we create items for all available indices across all fields
                    all_paths = {k: v["path"] for k, v in path_array_items.items()}
                    max_len = max(len(paths) for paths in all_paths.values())
                    
                    # Extract all values from all path arrays, preserving index positions
                    # aligned_values[k][i] = value at index i for field k
                    aligned_values = {}
                    for k, paths in all_paths.items():
                        aligned_values[k] = []
                        for p in paths:
                            try:
                                val = glom(root_data, p, default=None)
                                # Store None for empty strings to maintain index alignment
                                aligned_values[k].append(val if val != "" else None)
                            except Exception:
                                # Path extraction failed - store None to preserve index structure
                                aligned_values[k].append(None)
                    
                    # Sub-Case 1B-1a: In array context - create multiple aligned items
                    if array_context:
                        aligned_result = []
                        # Create one item per index, aligning all fields at the same index
                        for i in range(max_len):
                            item = {}
                            # Add all path array values at this index (aligned by index)
                            for k in all_paths.keys():
                                if i < len(aligned_values[k]) and aligned_values[k][i] is not None:
                                    item[k] = aligned_values[k][i]
                            # Add regular items (non-path-array fields) to each aligned item
                            # These are processed once and added to all items (e.g., a shared "type" field)
                            if regular_items:
                                for k, v in regular_items.items():
                                    processed_val = process_value(v, array_context=False)
                                    if processed_val is not None:
                                        item[k] = processed_val
                            # Only add items that have at least one non-None value
                            if item:
                                aligned_result.append(item)
                        return aligned_result if aligned_result else []
                    
                    # Sub-Case 1B-1b: Not in array context - use first value from each path array
                    result = {}
                    for k in all_paths.keys():
                        if aligned_values[k] and aligned_values[k][0] is not None:
                            result[k] = aligned_values[k][0]
                    # Add regular items normally
                    for k, v in regular_items.items():
                        processed_val = process_value(v, array_context=False)
                        if processed_val is not None:
                            result[k] = processed_val
                    return result
                
                # Case 1B-2: Single field with path array in array context - expansion case
                # Example: phones[].number with paths ["Phone1Number", "Phone2Number"]
                # The path array returns a list, and we need to expand the single-item dict into multiple items
                if array_context and len(items) == 1:
                    k, v = items[0]
                    # Process the value - if it's a path array, this will return a list
                    processed = process_value(v, array_context=True)
                    # If we got a list with multiple items, expand the dict into multiple dicts
                    if isinstance(processed, list) and len(processed) > 1:
                        return [{k: val} for val in processed if val is not None]
                
                # No path arrays - process normally
                if "id" not in value:
                    # TODO: create the proper identifier string for entity (currently using placeholder)
                    uid = uuid5(NAMESPACE, "some-identifier-string")
                    items.insert(0, ("id", str(uid)))
                
                # Determine if we're entering an array context by checking if any child is a list
                in_array = any(isinstance(v, list) for v in value.values())
                
                # Recursively process all items in the nested object
                # Pass template=k when there's a split and array_context always
                return {k: process_value(v, array_context=in_array, template=k) 
                if isinstance(v, dict) and "split" in v and "path" in v 
                else process_value(v, array_context=in_array)
                for k, v in items}
        # Case 2: Value is a list - processing an array structure (e.g., phones[])
        # When we encounter a list, we're definitely in an array context
        elif isinstance(value, list):
            # Sub-Case 2a: Special handling for split in arrays
            # Create array of objects if split and path are present
            if (len(value) == 1 and isinstance(value[0], dict) and len(value[0]) == 1):
                key, val = list(value[0].items())[0]
                if isinstance(val, dict) and "path" in val and "split" in val:
                    # Process the path spec with split, passing the key as template to wrap results.
                    processed = process_value(val, array_context=True, template=key)
                    return processed if isinstance(processed, list) else [processed]
            
            # Sub-Case 2b: Process items with array_context=True, 
            # This ensures that path arrays within array items are handled correctly
            processed = [process_value(item, array_context=True) for item in value]

            # Flatten if any items returned lists (from aligned path arrays)
            flattened = []
            for item in processed:
                if isinstance(item, list):
                    # Item was expanded into multiple items (from path array alignment)
                    flattened.extend(item)
                elif item:  # Skip None/empty items
                    flattened.append(item)
            return flattened if flattened else []

        # Case 3: Value is a primitive (string, number, bool, None, etc.)
        # Return the value as-is - no processing needed
        else:
            # Return scalar
            return value
    
    out = process_value(mapping_spec)

    return out

"""
GET_PROCESS_ORDER: Returns the order in which the inputted mapped HSDS entities should be processed with 
the first index representing the first entity to be processed. 
"""

def get_process_order(groups: List[(str, List[Dict[str, Any]])]) -> List[str]:
    keys = [k for (k, _) in groups]
    order = []

    if(len(keys) > 0):
        order.append(keys[0])

    for k in keys[1::]:
        idx = len(order)

        # Perform BFS through relationship DAG
        edges = HSDS_RELATIONS[k]
        while(len(edges) > 0):
            ent = edges[0]

            # Postition entity at an index that is before all its ancestors.
            if(ent in order):
                idx = min(idx, order.index(ent))

            edges = edges[1::] + HSDS_RELATIONS[ent]

        order.insert(idx, k)

    return order

"""
TRANSFORMS: Currently not using, but certainly may be useful in the future.
"""

Transform = Callable[[Any], Any]
TRANSFORMS: Dict[str, Transform] = {
    "int": int,
    "float": float,
    "str": str,
    "lower": lambda s: s.lower() if isinstance(s, str) else s,
    "upper": lambda s: s.upper() if isinstance(s, str) else s,
    "bool": bool,
    "date_from_iso": lambda s: date.fromisoformat(s) if isinstance(s, str) else s,
}


def register_transform(name: str, fn: Transform) -> None:
    TRANSFORMS[name] = fn

"""
MAP: Deals with the unnested case of layer 1. Essentially moving from a CSV with columns to a dictionary with fields.
Only a couple lines of this mapping function are actually being used (see comments) given how we currently parse our 
mapping and data csvs but the transforms especially may be useful later if we want to (for instance) split data.
"""

# def map(source: Any, mapping: Dict[str, Any]) -> Organization:
#     """
#     source: arbitrary object/dict with unknown shape until runtime
#     mapping: rules describing how to build Organization fields from source
#     """
#     if not isinstance(source, (dict, list, tuple)):
#         try:
#             source = vars(source)
#         except TypeError:
#             raise ValueError(
#                 "source must be a dict, list, tuple, or object with __dict__"
#             )
#     out: Dict[str, Any] = {}
#     for dest_field, rule in mapping.items():
#         if isinstance(rule, str):
#             # Since our rule is a dictionary, not relevant for our parser
#             out[dest_field] = glom(source, rule)
#         elif isinstance(rule, dict):
#             if "literal" in rule:
#                 # if "literal" is in the rule output it directly outputs it (not relevant for our parser)
#                 out[dest_field] = rule["literal"]
#                 continue
#             if "paths" in rule:
#                 # if there are more than one paths in the dictionary (not relevant for how we parse)
#                 spec = Coalesce(*rule["paths"], default=rule.get("default"))
#                 val = glom(source, spec)
#             else:
#                 # !!!! This is largely the only line that matters !!!!, though default doesn't currently do anything
#                 # since there's currently no "default" set in our parsing (we would likely need to change the format to
#                 # { "path" : "filename.path", "default": "something"})
#                 val = glom(source, rule.get("path"), default=rule.get("default"))
#             # potentially useful in the future if we want more rules (potentially splitting stuff?)
#             tname = rule.get("transform")
#             if tname:
#                 fn = TRANSFORMS.get(tname)
#                 targs = rule.get("transform_args", []) or []
#                 tkwargs = rule.get("transform_kwargs", {}) or {}
#                 val = fn(val, *targs, **tkwargs) if fn else val
#             out[dest_field] = val
#         else:
#             raise TypeError(f"Invalid mapping rule for field {dest_field}: {rule}")
#     return Organization.model_validate(out)

