from __future__ import annotations
from typing import Any, Callable, Dict, List
from datetime import date
from glom import glom, Coalesce
from uuid import UUID, uuid5
from .models import Organization
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
        
    def process_value(value, template=None):
        """
        Recursively processes mapping values to transform flat CSV data into nested structures.
        Handles three main cases: path specs (leaf data extraction), nested objects, and arrays.
        
        Args:
            value: The mapping spec or data value to process (dict, list, or scalar).
            template: The parent key name when processing a leaf path spec with split.
                      Used to wrap split parts in objects (e.g., {name: "part"}).
        """
        if isinstance(value, dict):
            if "path" in value:
                # Before extracting data, make sure the mapped input colum exists
                input_field = value["path"].split(".", 1)[1] # Extract the part after the first dot: "filename.column" -> column
                csv_row = list(root_data.values())[0] # Get the CSV row dict stored inside of root_data

                if input_field not in csv_row: # Check if column exists in the CSV row dictionary, if it doesn't throw error
                    raise KeyError(f"Input field '{input_field}' from mapping does not exist in the CSV data")
                
                # Extract the value from the root data using the glom path.
                extracted_val = glom(root_data, value["path"])
                
                # SUBCASE 1a: Path spec with split directive (comma-separated or other delimiter).
                if "split" in value and value["split"]:
                    split_char = value["split"]
                    if isinstance(extracted_val, str):
                        # Split on delimiter and strips brackets and whitespace
                        parts = [part.strip() for part in extracted_val.split(split_char) if part.strip()]
                        parts = [part.strip('{}') for part in parts]

                        # If template is provided, wrap each part with that key (e.g., [{"name": "English"}, {"name": "Spanish"}])
                        if template:
                            return [{template: part} for part in parts]
                        else:
                            # Otherwise return flat list of strings
                            return parts
                # No split, return as is
                return extracted_val
            else:
                # CASE 2: Handle nested objects without path
                items = list(value.items())

                if "id" not in value:
                    # TODO: create the proper identifier string for entity (currently using placeholder)
                    uid = uuid5(NAMESPACE, "some-identifier-string")
                    items.insert(0, ("id", str(uid)))
                
                # Process each key-value pair in the nested object and template is given to wrap split results
                return {k: process_value(v, k) if isinstance(v, dict) and "split" in v and "path" in v else process_value(v) for k, v in items}
        # CASE 3: Handle array values
        elif isinstance(value, list):
            # Create array of objects if split and path are present
            if (len(value) == 1 and isinstance(value[0], dict) and len(value[0]) == 1):
                key, val = list(value[0].items())[0]
                if isinstance(val, dict) and "path" in val and "split" in val:
                    # Process the path spec with split, passing the key as template to wrap results.
                    processed = process_value(val, key)
                    return processed if isinstance(processed, list) else [processed]

            # Process each item if regular array
            return [process_value(item) for item in value]
        else:
            # Return scalar
            return value
    
    out = process_value(mapping_spec)

    return out

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

def map(source: Any, mapping: Dict[str, Any]) -> Organization:
    """
    source: arbitrary object/dict with unknown shape until runtime
    mapping: rules describing how to build Organization fields from source
    """
    if not isinstance(source, (dict, list, tuple)):
        try:
            source = vars(source)
        except TypeError:
            raise ValueError(
                "source must be a dict, list, tuple, or object with __dict__"
            )
    out: Dict[str, Any] = {}
    for dest_field, rule in mapping.items():
        if isinstance(rule, str):
            # Since our rule is a dictionary, not relevant for our parser
            out[dest_field] = glom(source, rule)
        elif isinstance(rule, dict):
            if "literal" in rule:
                # if "literal" is in the rule output it directly outputs it (not relevant for our parser)
                out[dest_field] = rule["literal"]
                continue
            if "paths" in rule:
                # if there are more than one paths in the dictionary (not relevant for how we parse)
                spec = Coalesce(*rule["paths"], default=rule.get("default"))
                val = glom(source, spec)
            else:
                # !!!! This is largely the only line that matters !!!!, though default doesn't currently do anything
                # since there's currently no "default" set in our parsing (we would likely need to change the format to
                # { "path" : "filename.path", "default": "something"})
                val = glom(source, rule.get("path"), default=rule.get("default"))
            # potentially useful in the future if we want more rules (potentially splitting stuff?)
            tname = rule.get("transform")
            if tname:
                fn = TRANSFORMS.get(tname)
                targs = rule.get("transform_args", []) or []
                tkwargs = rule.get("transform_kwargs", {}) or {}
                val = fn(val, *targs, **tkwargs) if fn else val
            out[dest_field] = val
        else:
            raise TypeError(f"Invalid mapping rule for field {dest_field}: {rule}")
    return Organization.model_validate(out)

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
