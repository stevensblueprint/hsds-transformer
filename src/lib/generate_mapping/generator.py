from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


from ..maintenance.parse_json import fetch_json_from_url


@dataclass(frozen=True)
class FieldSpec:
    path: str
    description: str
    required: bool


def flatten_schema(schema: dict[str, Any]) -> list[FieldSpec]:
    if not isinstance(schema, dict):
        raise TypeError("schema must be a dict")

    rows: list[FieldSpec] = []

    def normalize_desc(value: Any) -> str:
        if not isinstance(value, str):
            return ""
        normalized = value.replace("\r", " ").replace("\n", " ")
        return " ".join(normalized.split()).strip()

    def join(prefix: str, part: str) -> str:
        if not prefix:
            return part
        return f"{prefix}.{part}"

    def iter_required(node: dict[str, Any]) -> set[str]:
        required: set[str] = set()
        for key in ("required", "tabular_required"):
            items = node.get(key)
            if isinstance(items, Iterable) and not isinstance(items, (str, bytes)):
                for item in items:
                    if isinstance(item, str):
                        required.add(item)
        return required

    def walk(node: Any, prefix: str, ancestors_required: bool) -> None:
        if not isinstance(node, dict):
            return

        # Handle composition keywords (allOf, oneOf, anyOf)
        for composition_key in ("allOf", "oneOf", "anyOf"):
            composition_value = node.get(composition_key)
            if isinstance(composition_value, list):
                if composition_key == "allOf":
                    # Collect and merge all "required" arrays from every dict entry
                    # so that required items declared in one sibling are applied
                    # when walking property definitions in other siblings
                    merged_required: set[str] = set()
                    for entry in composition_value:
                        if isinstance(entry, dict):
                            merged_required.update(iter_required(entry))
                    # Extend or create merged_ancestors_required based on current ancestors_required
                    # We inject the merged required set into each entry before walking
                    for entry in composition_value:
                        if isinstance(entry, dict):
                            # Create a shallow copy to inject merged required without mutating original
                            merged_entry = dict(entry)
                            existing_required = merged_entry.get("required", [])
                            if isinstance(existing_required, list):
                                merged_entry["required"] = list(merged_required)
                            else:
                                merged_entry["required"] = list(merged_required)
                            walk(merged_entry, prefix, ancestors_required)
                else:
                    for entry in composition_value:
                        if isinstance(entry, dict):
                            walk(entry, prefix, ancestors_required)

        node_type = node.get("type")
        properties = node.get("properties")
        if node_type == "object" or isinstance(properties, dict):
            props = properties if isinstance(properties, dict) else {}
            required_set = iter_required(node)
            for prop_name, prop_schema in props.items():
                if not isinstance(prop_name, str):
                    continue
                if not isinstance(prop_schema, dict):
                    continue

                is_array = prop_schema.get("type") == "array"
                part = f"{prop_name}[]" if is_array else prop_name
                prop_path = join(prefix, part)

                required_here = prop_name in required_set
                effective_required = ancestors_required and required_here

                rows.append(
                    FieldSpec(
                        path=prop_path,
                        description=normalize_desc(prop_schema.get("description")),
                        required=effective_required,
                    )
                )

                if is_array:
                    items = prop_schema.get("items")
                    if isinstance(items, dict):
                        walk(items, prop_path, effective_required)
                else:
                    if prop_schema.get("type") == "object" or isinstance(
                        prop_schema.get("properties"), dict
                    ):
                        walk(prop_schema, prop_path, effective_required)
            return

        if node_type == "array":
            items = node.get("items")
            if isinstance(items, dict):
                walk(items, prefix, ancestors_required)

    walk(schema, "", True)
    return rows


def _fetch_schema_from_url(url: str, *, timeout_s: int = 30) -> dict[str, Any]:
    """Fetch a schema over HTTP and return the parsed dictionary."""

    return fetch_json_from_url(url, timeout_s=timeout_s)


def _flatten_schema_from_url(url: str, *, timeout_s: int = 30) -> list[FieldSpec]:
    """Shortcut to flatten a schema fetched from *url*."""

    schema = _fetch_schema_from_url(url, timeout_s=timeout_s)
    return flatten_schema(schema)
