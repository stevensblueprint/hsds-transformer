import ast
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


def _extract_entity_name(node: dict, prop_name: str) -> str | None:
    """Get the canonical entity name from a schema node, or None if not an entity."""
    name = node.get("name")
    if name and isinstance(name, str):
        return name
    if node.get("type") == "object" or "properties" in node:
        return _singularize_property_name(prop_name)
    return None


def _add_parent(relations: dict[str, list[str]], entity: str, parent: str) -> None:
    """Append a parent to an entity's parent list if not already present."""
    if parent not in relations[entity]:
        relations[entity].append(parent)


def _discover_entities(
    schema_node: dict,
    relations: dict[str, list[str]],
    id_refs: dict[str, list[str]],
) -> None:
    """Recursively walk the schema to discover all HSDS entities and collect raw _id fields.

    _id fields are stored unfiltered in id_refs so they can be resolved later
    against the complete entity set, making the algorithm order-independent.
    """
    if not isinstance(schema_node, dict):
        return

    props = schema_node.get("properties", {})
    if not props:
        items = schema_node.get("items", {})
        if isinstance(items, dict):
            props = items.get("properties", {})
            schema_node = items

    for prop_name, prop_schema in props.items():
        if not isinstance(prop_schema, dict):
            continue

        # Array of objects = nested entity
        if prop_schema.get("type") == "array":
            items = prop_schema.get("items", {})
            if isinstance(items, dict) and (items.get("type") == "object" or "properties" in items):
                entity_name = _extract_entity_name(items, prop_name)
                if entity_name:
                    if entity_name not in relations:
                        relations[entity_name] = []
                        id_refs[entity_name] = []
                    # Collect raw _id fields without filtering — resolve later
                    for prop_n in items.get("properties", {}):
                        if prop_n.endswith("_id") and prop_n != "id":
                            id_refs[entity_name].append(prop_n[:-3])
                # Always recurse — entity may appear at multiple nesting levels
                _discover_entities(items, relations, id_refs)

        # Inline object = nested entity
        elif prop_schema.get("type") == "object" or "properties" in prop_schema:
            entity_name = _extract_entity_name(prop_schema, prop_name)
            if entity_name:
                if entity_name not in relations:
                    relations[entity_name] = []
                    id_refs[entity_name] = []
                for prop_n in prop_schema.get("properties", {}):
                    if prop_n.endswith("_id") and prop_n != "id":
                        id_refs[entity_name].append(prop_n[:-3])
            _discover_entities(prop_schema, relations, id_refs)


def _extract_id_refs(entity_node: dict, known_entities) -> list[str]:
    """Extract parent entity names from *_id fields in an entity schema."""
    parents = []
    props = entity_node.get("properties", {})
    known = set(known_entities)

    for prop_name in props:
        if prop_name.endswith("_id") and prop_name != "id":
            ref_name = prop_name[:-3]  # strip "_id"
            if ref_name in known:
                parents.append(ref_name)
            else:
                singular = _singularize_property_name(ref_name)
                if singular in known:
                    parents.append(singular)

    return parents


def generate_relations_dict(schema: dict[str, Any]) -> dict[str, list[str]]:
    """Parse JSON schema into a dictionary of HSDS relationships."""
    relations: dict[str, list[str]] = {}
    id_refs: dict[str, list[str]] = {}

    # Register the root entity
    root_name = _extract_entity_name(schema, "organization")
    if root_name:
        relations[root_name] = []
        id_refs[root_name] = []

    # Pass 1: Discover all entities and collect raw _id fields
    _discover_entities(schema, relations, id_refs)

    # Add any missing known HSDS entities as root entities
    all_hsds_entities = {
        "organization", "service", "location", "service_at_location",
        "address", "phone", "schedule", "service_area", "language", "funding",
        "accessibility", "cost_option", "program", "required_document", "contact",
        "organization_identifier", "service_capacity", "unit", "attribute", "url",
        "metadata", "meta_table_description", "taxonomy", "taxonomy_term"
    }
    for entity in all_hsds_entities:
        if entity not in relations:
            relations[entity] = []

    # Pass 2: Resolve _id refs against the complete entity set
    known_entities = set(relations.keys())
    for entity_name, raw_refs in id_refs.items():
        for ref in raw_refs:
            if ref in known_entities:
                _add_parent(relations, entity_name, ref)
            else:
                singular = _singularize_property_name(ref)
                if singular in known_entities:
                    _add_parent(relations, entity_name, singular)

    # --- Manual overrides for spec-level edge cases ---

    # service is a root entity (breaks cyclic dependency with organization/program)
    relations["service"] = []

    # Root entities with no parents
    relations["meta_table_description"] = []
    relations["taxonomy"] = []

    # taxonomy_term depends on attribute (not the other way around)
    relations["taxonomy_term"] = ["attribute"]

    # unit depends on service_capacity
    relations["unit"] = ["service_capacity"]

    # service_capacity only depends on service (unit is a child, not a parent)
    relations["service_capacity"] = ["service"]

    # Build entity ordering: core first, then alphabetical
    core_keys = ["organization", "service", "location", "service_at_location"]
    ordered_entities = list(core_keys)
    for key in sorted(relations.keys()):
        if key not in core_keys:
            ordered_entities.append(key)

    # attribute is polymorphic — applies to nearly all entities
    attribute_parents = [
        e for e in ordered_entities
        if e not in {"attribute", "metadata", "taxonomy", "taxonomy_term", "service_capacity"}
    ]
    relations["attribute"] = attribute_parents

    # metadata is polymorphic — applies to nearly all entities including attribute
    relations["metadata"] = [
        e for e in ordered_entities
        if e not in {"metadata", "service_capacity", "taxonomy_term"}
    ]

    # Remove self-loops
    for key, parents in relations.items():
        if key in parents:
            parents.remove(key)

    # Reverse edges: service depends on organization/program, so those entities
    # have service as a child in the DAG
    if "organization" in relations:
        _add_parent(relations, "organization", "service")
    if "program" in relations:
        _add_parent(relations, "program", "service")

    # Build final dict preserving entity ordering
    final_dict = {key: relations[key] for key in ordered_entities if key in relations}

    return final_dict


def write_relations_file(relations: dict[str, list[str]], out_path: str) -> None:
    """Write the dictionary to relations.py preserving the original docstring if possible."""
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
