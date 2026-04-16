"""
Tests for custom transform application in process_value / nested_map.

Covers:
  - Case 1A-2b: single path, no split — transform applied to scalar (title_case)
  - Case 1A-2b: single path, strip then transform — strip runs first (format_phone)
  - Case 1A-2a: single path, with split — transform applied to resolved list (sort_names)
  - Selectivity: fields without a transform key pass through unchanged
  - transreg=None: transform keys in mapping are silently ignored; strip/split still apply

Run from the project root:
    python tests/test_custom_transform.py
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lib.parser import parse_input_csv, parse_nested_mapping
from src.lib.mapper import nested_map
from src.lib.custom_transform.transforms_loader import TransformsRegistry

DATA_DIR = Path(__file__).parent.parent / "data" / "transform_test"
TRANSFORMS_MODULE = DATA_DIR / "transforms.py"


def load_test_data():
    input_rows = parse_input_csv(str(DATA_DIR / "organizations.csv"), "organizations")
    mapping, _ = parse_nested_mapping(
        str(DATA_DIR / "organizations_organization_mapping.csv"), "organizations"
    )
    return input_rows, mapping


def test_title_case_transform():
    """Case 1A-2b: 'acme nonprofit' → 'Acme Nonprofit' via title_case."""
    rows, mapping = load_test_data()
    reg = TransformsRegistry(TRANSFORMS_MODULE)
    result = nested_map(rows[0], mapping, transreg=reg)
    assert result["name"] == "Acme Nonprofit", f"Expected 'Acme Nonprofit', got {result['name']!r}"
    print("PASS: title_case applied to name")


def test_strip_then_format_phone():
    """Case 1A-2b: strip removes ()-  first, then format_phone inserts dashes."""
    rows, mapping = load_test_data()
    reg = TransformsRegistry(TRANSFORMS_MODULE)
    result = nested_map(rows[0], mapping, transreg=reg)
    assert result["phone"] == "303-617-2300", f"Expected '303-617-2300', got {result['phone']!r}"
    print("PASS: strip then format_phone applied to phone")


def test_sort_names_on_split_list():
    """Case 1A-2a: split on comma produces list, then sort_names sorts alphabetically."""
    rows, mapping = load_test_data()
    reg = TransformsRegistry(TRANSFORMS_MODULE)
    result = nested_map(rows[0], mapping, transreg=reg)
    names = [t["name"] for t in result["tags"]]
    assert names == ["tagA", "tagB", "tagC"], f"Expected sorted tags, got {names}"
    print("PASS: sort_names applied to split tags")


def test_no_transform_field_passthrough():
    """Fields with no transform key must be unaffected even when a registry is present."""
    rows, mapping = load_test_data()
    reg = TransformsRegistry(TRANSFORMS_MODULE)
    result = nested_map(rows[0], mapping, transreg=reg)
    assert result["id"] == "org-001", f"Expected 'org-001', got {result['id']!r}"
    print("PASS: id field without transform passes through unchanged")


def test_transreg_none_skips_transforms():
    """With transreg=None, transform keys are ignored; strip and split still apply."""
    rows, mapping = load_test_data()
    result = nested_map(rows[0], mapping, transreg=None)

    # title_case should NOT have run
    assert result["name"] == "acme nonprofit", f"Expected raw name, got {result['name']!r}"

    # strip still runs, but format_phone should NOT have run
    assert result["phone"] == "3036172300", f"Expected strip-only phone, got {result['phone']!r}"

    # split still runs, but sort_names should NOT have run — original CSV order preserved
    names = [t["name"] for t in result["tags"]]
    assert names == ["tagC", "tagA", "tagB"], f"Expected unsorted tags, got {names}"

    print("PASS: transreg=None skips transforms; strip and split still apply")


if __name__ == "__main__":
    test_title_case_transform()
    test_strip_then_format_phone()
    test_sort_names_on_split_list()
    test_no_transform_field_passthrough()
    test_transreg_none_skips_transforms()
    print("\nAll tests passed.")
