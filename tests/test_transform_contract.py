"""Regression coverage for the strict local custom-transform contract."""
import csv
import json

import pytest
from click.testing import CliRunner

from src.cli.main import main
from src.lib.transform.collections import build_collections
from src.lib.transform.json_collections import build_collections_from_json
from src.lib.transform.custom_transform.transforms_loader import TransformsRegistry
from src.lib.transform.custom_transform.custom_transform_error import CustomTransformError
from src.lib.transform.mapper import nested_map


def registry(tmp_path, code="transforms = {'uppercase': str.upper}"):
    path = tmp_path / "transforms.py"
    path.write_text(code, encoding="utf-8")
    return TransformsRegistry(path)


def dataset(tmp_path, fmt, name="uppercase", records=None):
    rows = records if records is not None else [{"id": "org-1", "name": "hello"}]
    mapping = tmp_path / f"organizations_organization_mapping.{fmt}"
    source = tmp_path / f"organizations.{fmt}"
    if fmt == "json":
        source.write_text(json.dumps(rows))
        mapping.write_text(json.dumps({"mappings": [
            {"output_path": "id", "input_path": "id"},
            {"output_path": "name", "input_path": "name", "transform": name},
        ]}))
    else:
        with source.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["id", "name"])
            writer.writeheader()
            writer.writerows(rows)
        with mapping.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows([
                ["path", "input_field", "split", "strip", "transform"],
                ["", "", "", "", ""],
                ["id", "id", "", "", ""], ["name", "name", "", "", name],
            ])
    return source, mapping


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_cli_executes_transform(tmp_path, fmt):
    dataset(tmp_path, fmt)
    registry(tmp_path)
    output = tmp_path / "output"
    result = CliRunner().invoke(main, [str(tmp_path), "-f", fmt,
        "--transforms", str(tmp_path / "transforms.py"), "-o", str(output)])
    assert result.exit_code == 0, result.output
    assert "loaded from" in result.output
    assert json.loads((output / "organization_org-1.json").read_text())["name"] == "HELLO"


@pytest.mark.parametrize("fmt", ["csv", "json"])
@pytest.mark.parametrize("mode", ["absent", "missing_file", "missing_name", "throwing"])
def test_cli_fails_explicitly(tmp_path, fmt, mode):
    dataset(tmp_path, fmt)
    args = [str(tmp_path), "-f", fmt, "-o", str(tmp_path / "output")]
    if mode != "absent":
        args += ["--transforms", str(tmp_path / "transforms.py")]
    if mode == "missing_name":
        registry(tmp_path, "transforms = {}")
    if mode == "throwing":
        registry(tmp_path, "def fail(value):\n    raise RuntimeError('boom')\ntransforms = {'uppercase': fail}")
    result = CliRunner().invoke(main, args)
    assert result.exit_code != 0
    assert not (tmp_path / "output").exists()
    if mode == "throwing":
        for context in ["uppercase", "boom", "Row index: 0", f"organizations.{fmt}", "mapping_path"]:
            assert context in result.output
    elif mode != "missing_file":
        assert "uppercase" in result.output
    else:
        assert "Cannot load custom transforms" in result.output


@pytest.mark.parametrize("code", [
    "", "transforms = []", "transforms = {'uppercase': 3}",
    "transforms = {1: str.upper}", "transforms = {'': str.upper}",
    "raise RuntimeError('import failed')", "def broken(:", 
])
def test_malformed_modules_are_diagnostic(tmp_path, code):
    with pytest.raises(ValueError, match="Cannot load custom transforms") as error:
        registry(tmp_path, code)
    assert "transforms.py" in str(error.value)
    assert error.value.__cause__ is not None


@pytest.mark.parametrize("fmt", ["csv", "json"])
@pytest.mark.parametrize("rows", [[], [{"id": "org-1", "name": ""}]])
def test_preflight_checks_empty_sources_and_blank_values(tmp_path, fmt, rows):
    dataset(tmp_path, fmt, records=rows)
    build = build_collections if fmt == "csv" else build_collections_from_json
    with pytest.raises(ValueError, match="uppercase"):
        build(str(tmp_path))


def test_preflight_checks_filtered_records(tmp_path):
    with pytest.raises(ValueError, match="unknown"):
        nested_map({"name": "hello"}, {"name": {"path": "name", "transform": "unknown"}},
                   transreg=registry(tmp_path), filter_spec={"path": "name", "value": "excluded"})


MAPPINGS = [
    {"path": "a", "transform": "uppercase"},
    {"path": ["a", "b"], "transform": "uppercase"},
    {"items": [{"name": {"path": ["a", "b"], "transform": "uppercase"}}]},
    {"attributes": [{"value": {"path": ["a", "b"], "transform": "uppercase"}}]},
    {"items": [{"name": {"path": ["a", "b"]}, "nested": {
        "value": {"path": ["a", "b"], "transform": "uppercase"}}}]},
    {"items": [{"name": {"path": ["a", "b"]}, "nested": [
        {"path": ["a", "b"], "transform": "uppercase"}]}]},
]


@pytest.mark.parametrize("mapping", MAPPINGS)
def test_throwing_transform_preserves_context(tmp_path, mapping):
    reg = registry(tmp_path, "def fail(value):\n    raise RuntimeError('boom')\ntransforms = {'uppercase': fail}")
    with pytest.raises(CustomTransformError) as caught:
        nested_map({"a": "hello", "b": "world"}, mapping, transreg=reg,
                   row_index=7, source_file="source.json", mapping_file="mapping.json")
    error = caught.value
    assert error.function_name == "uppercase"
    assert error.row_index == 7
    assert error.context["mapping_path"] == "a"
    assert error.context["source_file"] == "source.json"
    assert error.context["mapping_file"] == "mapping.json"
    assert isinstance(error.cause, RuntimeError)
    assert error.__cause__ is error.cause


def test_aligned_arrays_execute_and_keep_labels(tmp_path):
    mapping = {"attributes": [{"value": {"path": ["a", "b"], "transform": "uppercase"}}]}
    result = nested_map({"a": "hello", "b": "world"}, mapping, transreg=registry(tmp_path))
    assert result == {"attributes": [{"value": "HELLO", "label": "a"}, {"value": "WORLD", "label": "b"}]}


def test_no_declarations_needs_no_registry():
    assert nested_map({"a": "hello"}, {"name": {"path": "a"}}) == {"name": "hello"}


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_all_mappings_validated_before_first_call(tmp_path, fmt):
    _, mapping = dataset(tmp_path, fmt)
    second = tmp_path / f"organizations_service_mapping.{fmt}"
    second.write_text(mapping.read_text().replace("uppercase", "unknown"))
    calls = []

    class Registry:
        def get_transform(self, name):
            if name != "uppercase":
                raise ValueError("Unknown transform")
            return lambda value: calls.append(value) or value

    build = build_collections if fmt == "csv" else build_collections_from_json
    with pytest.raises(ValueError, match="unknown"):
        build(str(tmp_path), custom_transforms_registry=Registry())
    assert calls == []


def test_existing_custom_error_is_preserved(tmp_path):
    original = CustomTransformError("specific failure", function_name="inner", row_index=3)

    class Registry:
        def get_transform(self, name):
            def fail(value):
                raise original
            return fail

    with pytest.raises(CustomTransformError) as caught:
        nested_map({"a": "hello"}, MAPPINGS[1], transreg=Registry())
    assert caught.value is original
