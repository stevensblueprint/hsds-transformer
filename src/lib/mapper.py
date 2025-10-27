from __future__ import annotations
from typing import Any, Callable, Dict, List
import os
from dotenv import load_dotenv 
from datetime import date
from glom import glom, Coalesce
from uuid import UUID, uuid5
from .models import Organization
from .relations import HSDS_RELATIONS

# TODO: Initialize UUID with a proper fixed value
load_dotenv() # load environment vars
if "UUID_FIXED_VALUE" in os.environ:
    NAMESPACE = UUID(os.getenv("UUID_FIXED_VALUE"))

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
        
    def process_value(value):
        """
        Deals with every individual value in the dictionary
        Recursive to deal with the cases when the value is an dict or an array and has values inside
        """
        if isinstance(value, dict):
            if "path" in value:
                # This is a path specification - extract the value using ROOT data
                return glom(root_data, value["path"])
            else:
                # This is a nested object - process recursively
                items = list(value.items())

                if "id" not in value:
                    # TODO: create the proper identifier string for entity
                    uid = uuid5(NAMESPACE, os.getenv("UUID_IDENTIFIER_STRING"))
                    items.insert(0, ("id", str(uid)))
                
                return {k: process_value(v) for k, v in items}
        elif isinstance(value, list):
            # Process each item in the list
            return [process_value(item) for item in value]
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
