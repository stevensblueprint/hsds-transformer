"""
Tests for custom transform application in process_value / nested_map.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lib.transform.collections import build_collections
from src.lib.transform.custom_transform.custom_transform_error import CustomTransformError
from src.lib.transform.custom_transform.transforms_loader import TransformsRegistry
from src.lib.transform.mapper import nested_map
from src.lib.transform.parser import parse_input_csv, parse_nested_mapping

DATA_DIR = Path(__file__).parent.parent / "data" / "transform_test"
TRANSFORMS_MODULE = DATA_DIR / "transforms.py"


def load_test_data():
    input_rows = parse_input_csv(str(DATA_DIR / "organizations.csv"), "organizations")
    mapping, _ = parse_nested_mapping(
        str(DATA_DIR / "organizations_organization_mapping.csv"), "organizations"
    )
    return input_rows, mapping


def test_title_case_transform():
    rows, mapping = load_test_data()
    reg = TransformsRegistry(TRANSFORMS_MODULE)
    result = nested_map(rows[0], mapping, transreg=reg)
    assert result["name"] == "Acme Nonprofit"


def test_strip_then_format_phone():
    rows, mapping = load_test_data()
    reg = TransformsRegistry(TRANSFORMS_MODULE)
    result = nested_map(rows[0], mapping, transreg=reg)
    assert result["phone"] == "303-617-2300"


def test_sort_names_on_split_list():
    rows, mapping = load_test_data()
    reg = TransformsRegistry(TRANSFORMS_MODULE)
    result = nested_map(rows[0], mapping, transreg=reg)
    names = [t["name"] for t in result["tags"]]
    assert names == ["tagA", "tagB", "tagC"]


def test_no_transform_field_passthrough():
    rows, mapping = load_test_data()
    reg = TransformsRegistry(TRANSFORMS_MODULE)
    result = nested_map(rows[0], mapping, transreg=reg)
    assert result["id"] == "org-001"


def test_transreg_none_skips_transforms():
    rows, mapping = load_test_data()
    result = nested_map(rows[0], mapping, transreg=None)

    assert result["name"] == "acme nonprofit"
    assert result["phone"] == "3036172300"

    names = [t["name"] for t in result["tags"]]
    assert names == ["tagC", "tagA", "tagB"]


def test_nested_map_wraps_user_transform_errors():
    rows, mapping = load_test_data()

    class FailingRegistry:
        def get_transform(self, name):
            def fail(value):
                raise RuntimeError("boom")

            return fail

    captured_error = None
    try:
        nested_map(rows[0], mapping, transreg=FailingRegistry(), row_index=7)
        raise AssertionError("Expected CustomTransformError to be raised")
    except CustomTransformError as error:
        captured_error = error

    assert captured_error is not None
    error = captured_error
    assert error.function_name == "title_case"
    assert error.row_index == 7
    assert error.context["mapping_path"] == "organizations.name"
    assert isinstance(error.cause, RuntimeError)
    assert error.__cause__ is error.cause


def test_build_collections_applies_custom_transforms_registry():
    collections = build_collections(
        str(DATA_DIR),
        custom_transforms_registry=TransformsRegistry(TRANSFORMS_MODULE),
    )

    assert collections[0][0] == "organization"
    assert collections[0][1][0]["name"] == "Acme Nonprofit"
    assert collections[0][1][0]["phone"] == "303-617-2300"


if __name__ == "__main__":
    test_title_case_transform()
    test_strip_then_format_phone()
    test_sort_names_on_split_list()
    test_no_transform_field_passthrough()
    test_transreg_none_skips_transforms()
    test_nested_map_wraps_user_transform_errors()
    test_build_collections_applies_custom_transforms_registry()
