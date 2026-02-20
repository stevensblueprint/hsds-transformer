import ast
from collections import defaultdict
from typing import Any


def _singularize_property_name(prop_name: str) -> str:
    """Map plural property names from JSON schema to singular HSDS entity names."""
    if prop_name in ("physical_addresses", "addresses", "address"):
        return "address"
    if prop_name in ("organization_identifiers", "organization_identifier"):
        return "organization_identifier"
    if prop_name in ("capacities", "capacity", "service_capacities", "service_capacity"):
        return "service_capacity"
    if prop_name in ("taxonomy_details", "taxonomy_detail"):
        return "taxonomy_term"
    # To handle 3.2 updates vs 3.1.2 naming where urls were just url
    if prop_name in ("additional_urls", "additional_url", "additional_websites", "additional_website", "url"):
        return "url"

    if prop_name.endswith("ies"):
        return prop_name[:-3] + "y"
    if prop_name.endswith("s") and prop_name not in ["status"]:
        return prop_name[:-1]

    return prop_name


def _traverse_schema(node: Any, parent_name: str, relations: defaultdict[str, set[str]]) -> None:
    """Recursively search for properties and array items to build parent-child relations."""
    if not isinstance(node, dict):
        return

    properties = node.get("properties", {})
    for prop_name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            continue

        p_type = prop_schema.get("type")
        if p_type == "array":
            items = prop_schema.get("items", {})
            if isinstance(items, dict) and (items.get("type") == "object" or "properties" in items):
                child_name = _singularize_property_name(prop_name)
                if parent_name:
                    relations[child_name].add(parent_name)
                _traverse_schema(items, child_name, relations)

        elif p_type == "object" or "properties" in prop_schema:
            child_name = _singularize_property_name(prop_name)
            if parent_name:
                relations[child_name].add(parent_name)
            _traverse_schema(prop_schema, child_name, relations)


def generate_relations_dict(schema: dict[str, Any]) -> dict[str, list[str]]:
    """Parse JSON schema into a dictionary of HSDS relationships."""
    relations: defaultdict[str, set[str]] = defaultdict(set)
    
    # organization is typically the root of the datapackage/schema we ingest
    _traverse_schema(schema, "organization", relations)

    # Ensure root is present
    if "organization" not in relations:
        relations["organization"] = set()

    # Manual Overrides for Edge Cases present in HSDS 3.1.2 mapping
    # 1. 'attribute' and 'metadata' are polymorphic and don't natively nest everything in the schema.
    # We want them to point to basically all entities.
    all_entities = set(relations.keys())
    # from relations.py, attributes usually covers almost everything except itself, taxonomy, metadata
    attribute_parents = all_entities - {"attribute", "metadata", "taxonomy", "taxonomy_term", "meta_table_description"}
    relations["attribute"].update(attribute_parents)
    
    metadata_parents = all_entities - {"metadata", "meta_table_description"}
    relations["metadata"].update(metadata_parents)

    # 2. 'taxonomy_term' vs 'attribute' direction
    # the schema nests taxonomy_term under attribute, but conceptually attribute uses taxonomy_term.
    # We will ensure taxonomy_term depends on attribute as in the original relations.py
    if "attribute" in relations.get("taxonomy_term", set()):
        relations["taxonomy_term"].remove("attribute")
    relations["taxonomy_term"].add("attribute")
    if "taxonomy_term" in relations.get("attribute", set()):
         relations["attribute"].remove("taxonomy_term")
    # Remove self loops
    for key, parents in relations.items():
        if key in parents:
            parents.remove(key)

    # Clear cyclic explicit dependencies if any (e.g., service might have picked up organization)
    relations["service"] = set()

    # Create the final sorted dict (keys sorted, values sorted)
    final_dict = {}
    
    # Custom sort order to mimic Core first, then Other
    # Though we can just alphabetically sort them for consistency, matching original is nice
    core_keys = ["organization", "service", "location", "service_at_location"]
    
    for key in core_keys:
        if key in relations:
            final_dict[key] = sorted(list(relations[key]))
            
    for key in sorted(relations.keys()):
        if key not in core_keys:
            final_dict[key] = sorted(list(relations[key]))

    return final_dict


def write_relations_file(relations: dict[str, list[str]], out_path: str) -> None:
    """Write the dictionary to relations.py preserving the original docstring if possible."""
    # Build dictionary literal
    dict_content = "HSDS_RELATIONS = {\n"
    for i, (key, parents) in enumerate(relations.items()):
        dict_content += f'    "{key}": [\n'
        for j, parent in enumerate(parents):
            dict_content += f'        "{parent}"'
            if j < len(parents) - 1:
                dict_content += ",\n"
            else:
                dict_content += "\n"
        dict_content += "    ]"
        if i < len(relations) - 1:
            dict_content += ",\n\n"
        else:
            dict_content += "\n"
    dict_content += "}\n"

    # Default Docstring
    docstring = '"""\nDAG model of HSDS entity relationships.\n"""\n\n'
    
    # Try to grab existing docstring
    try:
        with open(out_path, "r", encoding="utf-8") as f:
            source = f.read()
            module = ast.parse(source)
            existing_doc = ast.get_docstring(module)
            if existing_doc:
                docstring = f'"""\n{existing_doc}\n"""\n\n'
    except Exception:
        pass

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(docstring)
        f.write(dict_content)
