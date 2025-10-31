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

def nested_map(data: Any, mapping_spec: Dict[str, Any], root_data=None) -> Organization:
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
        
    def process_value(value, array_context=False):
        """
        Deals with every individual value in the dictionary
        Recursive to deal with the cases when the value is an dict or an array and has values inside
        
        Args:
            value: The value to process
            array_context: Whether we're inside an array context (for aligning multiple fields)
        """
        if isinstance(value, dict):
            if "path" in value:
                # This is a path specification - extract the value using ROOT data
                path = value["path"]
                
                # Check if path is a list (multiple input fields)
                if isinstance(path, list):
                    # Extract values from all paths
                    extracted_values = []
                    for p in path:
                        try:
                            val = glom(root_data, p, default=None)
                            # Convert empty strings to None for filtering
                            if val == "" or val is None:
                                val = None
                            extracted_values.append(val)
                        except Exception:
                            extracted_values.append(None)
                    
                    # If we're in an array context, return all values (including None) for proper alignment
                    # Filtering happens at the alignment stage
                    if array_context:
                        return extracted_values
                    else:
                        # Not in array context - filter None and return appropriately
                        filtered = [v for v in extracted_values if v is not None]
                        return filtered if len(filtered) > 1 else (filtered[0] if filtered else None)
                else:
                    # Single path (existing behavior)
                    val = glom(root_data, path, default=None)
                    return val if val != "" else None
            else:
                # This is a nested object - process recursively
                items = list(value.items())
                
                # Track which items have path arrays
                path_array_items = {}
                regular_items = {}
                
                for k, v in items:
                    if isinstance(v, dict) and "path" in v and isinstance(v.get("path"), list):
                        path_array_items[k] = v
                    else:
                        regular_items[k] = v
                
                # If we have path arrays, handle alignment
                if path_array_items:
                    all_paths = {k: v["path"] for k, v in path_array_items.items()}
                    max_len = max(len(paths) for paths in all_paths.values())
                    
                    # Extract all values from path arrays
                    aligned_values = {}
                    for k, paths in all_paths.items():
                        aligned_values[k] = []
                        for p in paths:
                            try:
                                val = glom(root_data, p, default=None)
                                aligned_values[k].append(val if val != "" else None)
                            except Exception:
                                aligned_values[k].append(None)
                    
                    # If we're in array context, create multiple aligned items
                    if array_context:
                        aligned_result = []
                        for i in range(max_len):
                            item = {}
                            # Add all aligned path array values at this index
                            for k in all_paths.keys():
                                if i < len(aligned_values[k]) and aligned_values[k][i] is not None:
                                    item[k] = aligned_values[k][i]
                            # Add regular items (processed normally) to each aligned item
                            if regular_items:
                                for k, v in regular_items.items():
                                    processed_val = process_value(v, array_context=False)
                                    if processed_val is not None:
                                        item[k] = processed_val
                            if item:  # Only add non-empty items
                                aligned_result.append(item)
                        return aligned_result if aligned_result else []
                    
                    # Not in array context - process first values from path arrays
                    result = {}
                    for k in all_paths.keys():
                        if aligned_values[k] and aligned_values[k][0] is not None:
                            result[k] = aligned_values[k][0]
                    # Add regular items
                    for k, v in regular_items.items():
                        processed_val = process_value(v, array_context=False)
                        if processed_val is not None:
                            result[k] = processed_val
                    return result
                
                # Special case: single field with path array that returned a list in array context
                # This happens when processing like phones[].number with multiple paths
                # We need to expand the dict into multiple items
                if array_context and len(items) == 1:
                    k, v = items[0]
                    processed = process_value(v, array_context=True)
                    if isinstance(processed, list) and len(processed) > 1:
                        # Expand into multiple items
                        return [{k: val} for val in processed if val is not None]
                
                # No path arrays - process normally
                if "id" not in value:
                    # TODO: create the proper identifier string for entity
                    uid = uuid5(NAMESPACE, "some-identifier-string")
                    items.insert(0, ("id", str(uid)))
                
                # Determine if we're entering an array context
                in_array = any(isinstance(v, list) for v in value.values())
                
                return {k: process_value(v, array_context=in_array) for k, v in items}
        elif isinstance(value, list):
            # Process each item in the list - array context is True here
            processed = [process_value(item, array_context=True) for item in value]
            # Flatten if any items returned lists (from aligned path arrays)
            flattened = []
            for item in processed:
                if isinstance(item, list):
                    flattened.extend(item)
                elif item:  # Skip None/empty items
                    flattened.append(item)
            return flattened if flattened else []
        else:
            # Return the value as-is
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
