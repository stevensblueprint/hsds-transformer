from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class FieldSpec:
    """A single row entry describing a field in the flattened schema."""

    path: str
    description: str
    required: bool


def flatten_schema(schema: dict[str, Any]) -> list[FieldSpec]:
    """Walk *schema* and return a list of rows describing each scalar field.

    The returned paths use dot notation and append `[]` for array targets. Each
    ``FieldSpec`` also normalizes descriptions and tracks whether the field is
    required along the ancestor chain.
    """

    if not isinstance(schema, dict):
        raise TypeError("schema must be a dict")

    rows: list[FieldSpec] = []
    seen: set[str] = set()

    def normalize_desc(value: Any) -> str:
        """Return a single-line, whitespace-normalized description."""

        if not isinstance(value, str):
            return ""
        normalized = value.replace("\r", " ").replace("\n", " ")
        return " ".join(normalized.split()).strip()

    def join(prefix: str, part: str) -> str:
        """Concatenate the path prefix and the next segment."""

        if not prefix:
            return part
        return f"{prefix}.{part}"

    def iter_required(node: dict[str, Any]) -> set[str]:
        """Return the combined required/property lists for *node*."""

        required: set[str] = set()
        for key in ("required", "tabular_required"):
            items = node.get(key)
            if isinstance(items, Iterable) and not isinstance(items, (str, bytes)):
                for item in items:
                    if isinstance(item, str):
                        required.add(item)
        return required

    def walk(node: Any, prefix: str, ancestors_required: bool) -> None:
        """Recursively walk *node*, emitting FieldSpecs for each property."""

        if not isinstance(node, dict):
            return

        node_type = node.get("type")
        properties = node.get("properties")

        # Process direct properties first so the node's own metadata
        # (description, required) takes precedence via the ``seen`` set
        # when composition subschemas define overlapping fields.
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

                if prop_path not in seen:
                    seen.add(prop_path)
                    rows.append(
                        FieldSpec(
                            path=prop_path,
                            description=normalize_desc(prop_schema.get("description")),
                            required=effective_required,
                        )
                    )

                    # Recurse into children only on the first encounter to
                    # avoid wasted duplicate walks when composition
                    # subschemas later re-visit the same subtree.
                    if is_array:
                        items = prop_schema.get("items")
                        if isinstance(items, dict):
                            walk(items, prop_path, effective_required)
                    else:
                        if prop_schema.get("type") == "object" or isinstance(
                            prop_schema.get("properties"), dict
                        ):
                            walk(prop_schema, prop_path, effective_required)
                        elif any(
                            isinstance(prop_schema.get(k), list)
                            for k in ("allOf", "oneOf", "anyOf")
                        ):
                            # Delegate to walk so allOf required-merging and
                            # nested composition are handled by the
                            # top-level logic.
                            walk(prop_schema, prop_path, effective_required)

        # Handle composition keywords (allOf, oneOf, anyOf) *after* direct
        # properties so that the node's own definitions win first-writer
        # deduplication.
        for composition_key in ("allOf", "oneOf", "anyOf"):
            composition_value = node.get(composition_key)
            if isinstance(composition_value, list):
                if composition_key == "allOf":
                    # Collect and merge all "required" arrays from every
                    # dict entry so that required items declared in one
                    # sibling are applied when walking property definitions
                    # in other siblings.
                    merged_required: set[str] = set()
                    for entry in composition_value:
                        if isinstance(entry, dict):
                            merged_required.update(iter_required(entry))
                    for entry in composition_value:
                        if isinstance(entry, dict):
                            # Shallow copy to inject merged required
                            # without mutating the original schema.
                            merged_entry = dict(entry)
                            merged_entry["required"] = list(merged_required)
                            # Clear tabular_required so iter_required only
                            # sees the consolidated list via "required".
                            merged_entry.pop("tabular_required", None)
                            walk(merged_entry, prefix, ancestors_required)
                else:
                    for entry in composition_value:
                        if isinstance(entry, dict):
                            walk(entry, prefix, ancestors_required)

        if node_type == "array":
            items = node.get("items")
            if isinstance(items, dict):
                walk(items, prefix, ancestors_required)

    walk(schema, "", True)
    return rows
