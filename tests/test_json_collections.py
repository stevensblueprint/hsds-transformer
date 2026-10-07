import sys
import os
import json
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lib.transform.json_collections import (
    parse_input_json,
    parse_json_mapping,
    build_collections_from_json,
)
from src.lib.transform.collections import searching_and_assigning

DATA_DIR = Path("data")


# ---------------------------------------------------------------------------
# parse_input_json
# ---------------------------------------------------------------------------

class TestParseInputJson:
    def test_valid_array(self, tmp_path):
        p = tmp_path / "orgs.json"
        p.write_text(json.dumps([{"id": "1", "name": "Acme"}]))
        rows = parse_input_json(str(p), "orgs")
        assert len(rows) == 1
        assert rows[0] == {"orgs": {"id": "1", "name": "Acme"}}

    def test_non_array_raises(self, tmp_path):
        p = tmp_path / "orgs.json"
        p.write_text(json.dumps({"id": "1"}))
        with pytest.raises(ValueError, match="top-level array"):
            parse_input_json(str(p), "orgs")

    def test_empty_array(self, tmp_path):
        p = tmp_path / "orgs.json"
        p.write_text(json.dumps([]))
        rows = parse_input_json(str(p), "orgs")
        assert rows == []

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "orgs.json"
        p.write_text("{bad json")
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_input_json(str(p), "orgs")

    def test_values_stringified(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text(json.dumps([{"count": 42, "active": True, "empty": None}]))
        rows = parse_input_json(str(p), "data")
        row = rows[0]["data"]
        assert row["count"] == "42"
        assert row["active"] == "True"
        assert row["empty"] == ""

    def test_skips_non_dict_records(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text(json.dumps([{"id": "1"}, "not a dict", {"id": "2"}]))
        rows = parse_input_json(str(p), "data")
        assert len(rows) == 2


# ---------------------------------------------------------------------------
# parse_json_mapping
# ---------------------------------------------------------------------------

class TestParseJsonMapping:
    def test_valid_mapping(self, tmp_path):
        mapping_data = {
            "mappings": [
                {"output_path": "id", "input_path": "ID"},
                {"output_path": "name", "input_path": "Name"},
            ]
        }
        p = tmp_path / "orgs_organization_mapping.json"
        p.write_text(json.dumps(mapping_data))
        spec, filter_spec = parse_json_mapping(str(p), "orgs")

        assert filter_spec is None
        assert "id" in spec
        assert spec["id"]["path"] == "orgs.ID"
        assert spec["name"]["path"] == "orgs.Name"

    def test_with_filter(self, tmp_path):
        mapping_data = {
            "filter": {"column": "Status", "value": "Active"},
            "mappings": [{"output_path": "id", "input_path": "ID"}],
        }
        p = tmp_path / "m.json"
        p.write_text(json.dumps(mapping_data))
        _, filter_spec = parse_json_mapping(str(p), "orgs")

        assert filter_spec == {"column": "Status", "value": "Active"}

    def test_semicolon_paths(self, tmp_path):
        mapping_data = {
            "mappings": [
                {"output_path": "phones[].number", "input_path": "Phone1;Phone2"},
            ]
        }
        p = tmp_path / "m.json"
        p.write_text(json.dumps(mapping_data))
        spec, _ = parse_json_mapping(str(p), "orgs")

        assert "phones" in spec
        leaf = spec["phones"][0]["number"]
        assert leaf["path"] == ["orgs.Phone1", "orgs.Phone2"]

    def test_split_and_strip(self, tmp_path):
        mapping_data = {
            "mappings": [
                {"output_path": "tags[]", "input_path": "Tags", "split": ",", "strip": "<>"},
            ]
        }
        p = tmp_path / "m.json"
        p.write_text(json.dumps(mapping_data))
        spec, _ = parse_json_mapping(str(p), "orgs")

        leaf = spec["tags"][0]
        assert leaf["split"] == ","
        assert leaf["strip"] == "<>"

    def test_invalid_json_raises(self, tmp_path):
        p = tmp_path / "m.json"
        p.write_text("{bad")
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_json_mapping(str(p), "orgs")

    def test_missing_mappings_key(self, tmp_path):
        p = tmp_path / "m.json"
        p.write_text(json.dumps({"filter": {}}))
        with pytest.raises(ValueError, match="missing required 'mappings'"):
            parse_json_mapping(str(p), "orgs")

    def test_empty_mappings(self, tmp_path):
        p = tmp_path / "m.json"
        p.write_text(json.dumps({"mappings": []}))
        with pytest.raises(ValueError, match="empty or invalid"):
            parse_json_mapping(str(p), "orgs")

    def test_missing_output_path(self, tmp_path):
        p = tmp_path / "m.json"
        p.write_text(json.dumps({"mappings": [{"input_path": "ID"}]}))
        with pytest.raises(ValueError, match="missing.*output_path"):
            parse_json_mapping(str(p), "orgs")

    def test_not_object_raises(self, tmp_path):
        p = tmp_path / "m.json"
        p.write_text(json.dumps([1, 2, 3]))
        with pytest.raises(ValueError, match="JSON object"):
            parse_json_mapping(str(p), "orgs")


# ---------------------------------------------------------------------------
# build_collections_from_json
# ---------------------------------------------------------------------------

class TestBuildCollectionsFromJson:
    def test_no_json_mappings_returns_empty(self, tmp_path):
        (tmp_path / "orgs.csv").write_text("id\n1")
        result = build_collections_from_json(str(tmp_path))
        assert result == []

    def test_end_to_end(self):
        """Uses the data/json_test fixtures to run a full build."""
        path = DATA_DIR / "json_test"
        results = build_collections_from_json(str(path))

        results_dict = {name: objs for name, objs in results}
        assert "organization" in results_dict

        orgs = results_dict["organization"]
        assert len(orgs) == 1
        org = orgs[0]

        assert org["id"] == "1"
        assert org["name"] == "Test Organization"

        # Strip
        assert org["description"] == "Clean Me"

        # Split (templated)
        assert len(org["languages"]) == 2
        assert org["languages"][0]["name"] == "en"

        # Aligned arrays
        assert len(org["phones"]) == 2
        assert org["phones"][0]["number"] == "555-0100"
        assert org["phones"][0]["type"] == "Office"
        assert org["phones"][1]["number"] == "555-0101"
        assert org["phones"][1]["type"] == "Mobile"

        # Attributes with labels
        wifi = next((a for a in org["attributes"] if a["value"] == "HasWifi"), None)
        assert wifi is not None
        assert wifi["label"] == "Feature1"

        # Flat split
        assert "tagA" in org["tags"]
        assert "tagB" in org["tags"]

    def test_validation_error_on_bad_path(self, tmp_path):
        """Mapping references a field that doesn't exist in source JSON."""
        source = tmp_path / "data.json"
        source.write_text(json.dumps([{"id": "1", "name": "Org"}]))

        mapping = tmp_path / "data_organization_mapping.json"
        mapping.write_text(json.dumps({
            "mappings": [
                {"output_path": "id", "input_path": "id"},
                {"output_path": "name", "input_path": "nonexistent_field"},
            ]
        }))

        with pytest.raises(ValueError, match="do not exist in the input data"):
            build_collections_from_json(str(tmp_path))

    def test_filter_excludes_rows(self, tmp_path):
        source = tmp_path / "data.json"
        source.write_text(json.dumps([
            {"id": "1", "name": "Active Org", "status": "active"},
            {"id": "2", "name": "Inactive Org", "status": "inactive"},
        ]))

        mapping = tmp_path / "data_organization_mapping.json"
        mapping.write_text(json.dumps({
            "filter": {"column": "status", "value": "active"},
            "mappings": [
                {"output_path": "id", "input_path": "id"},
                {"output_path": "name", "input_path": "name"},
            ]
        }))

        results = build_collections_from_json(str(tmp_path))
        orgs = results[0][1]
        assert len(orgs) == 1
        assert orgs[0]["name"] == "Active Org"

    def test_skips_missing_source_file(self, tmp_path):
        """Mapping exists but no matching .json source — should skip, not error."""
        mapping = tmp_path / "missing_organization_mapping.json"
        mapping.write_text(json.dumps({
            "mappings": [{"output_path": "id", "input_path": "id"}]
        }))
        results = build_collections_from_json(str(tmp_path))
        assert results == []


# ---------------------------------------------------------------------------
# Integration: JSON collections -> searching_and_assigning
# ---------------------------------------------------------------------------

class TestJsonIntegration:
    def test_json_collections_feed_searching_and_assigning(self):
        """Verify JSON-built collections are compatible with the linking step."""
        path = DATA_DIR / "json_test"
        collections = build_collections_from_json(str(path))
        # Should not raise
        result = searching_and_assigning(collections)
        result_dict = {name: objs for name, objs in result}
        assert "organization" in result_dict
        assert len(result_dict["organization"]) == 1


def _write_json_source(directory, source, records, object_type="organization", filter_spec=None):
    (directory / f"{source}.json").write_text(json.dumps(records))
    mapping = {
        "mappings": [
            {"output_path": field, "input_path": field}
            for field in ("id", "name")
        ],
    }
    if filter_spec is not None:
        mapping["filter"] = filter_spec
    (directory / f"{source}_{object_type}_mapping.json").write_text(json.dumps(mapping))


@pytest.mark.parametrize("source_count", [2, 3])
def test_repeated_json_types_survive_build_link_and_write(tmp_path, source_count):
    from src.lib.transform.outputs import save_objects_to_json

    expected = [
        {"id": chr(ord("a") + index), "name": f"Organization {index}"}
        for index in range(source_count)
    ]
    for record in expected:
        _write_json_source(tmp_path, record["id"], [record])

    collections = build_collections_from_json(str(tmp_path))
    assert [name for name, _ in collections] == ["organization"]
    assert sorted(collections[0][1], key=lambda obj: obj["id"]) == expected

    linked = searching_and_assigning(collections)
    assert [name for name, _ in linked] == ["organization"]
    assert sorted(linked[0][1], key=lambda obj: obj["id"]) == expected

    output = tmp_path / "output"
    save_objects_to_json(linked, str(output))
    files = sorted(output.glob("*.json"))
    assert [file.name for file in files] == [
        f"organization_{record['id']}.json" for record in expected
    ]
    assert [json.loads(file.read_text()) for file in files] == expected


@pytest.mark.parametrize("empty_first", [True, False])
@pytest.mark.parametrize("filtered", [True, False])
def test_empty_or_filtered_json_source_does_not_replace_other_sources(
    tmp_path, monkeypatch, empty_first, filtered,
):
    expected = [{"id": "a", "name": "Alpha"}, {"id": "b", "name": "Beta"}]
    empty_records = [{"id": "excluded", "name": "Excluded", "status": "inactive"}] if filtered else []
    filter_spec = {"column": "status", "value": "active"} if filtered else None
    sources = [
        ("a", [expected[0]], None),
        ("b", [expected[1]], None),
    ]
    sources.insert(0 if empty_first else 2, ("empty", empty_records, filter_spec))
    for source, records, source_filter in sources:
        _write_json_source(tmp_path, source, records, filter_spec=source_filter)

    # Explicitly exercise both discovery orders; filesystem order is unspecified.
    mapping_files = [tmp_path / f"{source}_organization_mapping.json" for source, _, _ in sources]
    monkeypatch.setattr(Path, "glob", lambda self, pattern: iter(mapping_files))
    collections = build_collections_from_json(str(tmp_path))
    assert [name for name, _ in collections] == ["organization"]
    assert sorted(collections[0][1], key=lambda obj: obj["id"]) == expected
    linked = searching_and_assigning(collections)
    assert [name for name, _ in linked] == ["organization"]
    assert sorted(linked[0][1], key=lambda obj: obj["id"]) == expected


def test_repeated_json_ids_are_preserved_for_shared_integrity_validation(tmp_path):
    # Collection accumulation must not choose a winner or hide duplicate IDs.
    expected = [{"id": "same", "name": "Alpha"}, {"id": "same", "name": "Beta"}]
    for source, record in zip(("a", "b"), expected):
        _write_json_source(tmp_path, source, [record])

    collections = build_collections_from_json(str(tmp_path))
    assert [name for name, _ in collections] == ["organization"]
    assert sorted(collections[0][1], key=lambda obj: obj["name"]) == expected
    linked = searching_and_assigning(collections)
    assert len(linked) == 1
    assert sorted(linked[0][1], key=lambda obj: obj["name"]) == expected


def test_repeated_json_types_match_csv_object_graph(tmp_path):
    import csv
    from src.lib.transform.collections import build_collections

    for source, object_type, record in [
        ("a", "organization", {"id": "a", "name": "Alpha"}),
        ("b", "organization", {"id": "b", "name": "Beta"}),
        ("c", "location", {"id": "c", "name": "Center"}),
    ]:
        _write_json_source(tmp_path, source, [record], object_type=object_type)
        with (tmp_path / f"{source}.csv").open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["id", "name"])
            writer.writeheader()
            writer.writerow(record)
        (tmp_path / f"{source}_{object_type}_mapping.csv").write_text(
            "path,input_files_field\n,\nid,id\nname,name\n"
        )

    def canonical(collections):
        assert len({name for name, _ in collections}) == len(collections)
        return sorted((name, sorted(objects, key=lambda obj: obj["id"])) for name, objects in collections)

    json_collections = build_collections_from_json(str(tmp_path))
    csv_collections = build_collections(str(tmp_path))
    assert canonical(json_collections) == canonical(csv_collections)
    assert canonical(searching_and_assigning(json_collections)) == canonical(searching_and_assigning(csv_collections))
