import json

import pytest

from src.lib.transform.outputs import save_objects_to_json


@pytest.mark.parametrize("record", [{}, {"id": None}, {"id": ""}, {"id": " \t"}, {"id": 0}, {"id": False}])
@pytest.mark.parametrize("existing", [False, True])
def test_missing_id_last_leaves_output_untouched(tmp_path, record, existing):
    output = tmp_path / "output"
    if existing:
        output.mkdir()
        (output / "organization_ok.json").write_bytes(b"original")
        (output / "stale.json").write_bytes(b"stale")
    before = {p.name: p.read_bytes() for p in output.iterdir()} if existing else {}
    with pytest.raises(ValueError, match="Missing nonempty output ID.*group 1, record 2"):
        save_objects_to_json([("organization", [{"id": "ok"}, record])], output)
    assert output.exists() == existing
    assert ({p.name: p.read_bytes() for p in output.iterdir()} if existing else {}) == before


@pytest.mark.parametrize("separate_groups", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_duplicate_last_leaves_output_untouched(tmp_path, separate_groups, existing):
    output = tmp_path / "output"
    if existing:
        output.mkdir()
        (output / "organization_same.json").write_bytes(b"original")
    before = {p.name: p.read_bytes() for p in output.iterdir()} if existing else {}
    first = {"id": "same", "name": "First"}
    second = {"id": "same", "name": "Second"}
    groups = [("organization", [first, second])]
    if separate_groups:
        groups = [("organization", [first]), ("organization", [second])]
    with pytest.raises(ValueError, match="Duplicate output target.*first seen at"):
        save_objects_to_json(groups, output)
    assert output.exists() == existing
    assert ({p.name: p.read_bytes() for p in output.iterdir()} if existing else {}) == before
    assert first["name"] == "First"
    assert second["name"] == "Second"


def test_valid_distinct_outputs_and_one_shot_iterators(tmp_path):
    groups = iter([
        ("organization", iter([{"id": "one", "name": "Café"}])),
        ("organization", iter([{"id": "two"}])),
        ("service", iter([{"id": "one"}])),
    ])
    save_objects_to_json(groups, tmp_path)
    actual = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in tmp_path.iterdir()}
    assert actual == {
        "organization_one.json": {"id": "one", "name": "Café"},
        "organization_two.json": {"id": "two"},
        "service_one.json": {"id": "one"},
    }


@pytest.mark.parametrize("groups", [
    [("organization", [{"id": 1}, {"id": "1"}])],
    [("service_at", [{"id": "location_x"}]), ("service_at_location", [{"id": "x"}])],
])
def test_distinct_identities_with_same_filename_are_rejected(tmp_path, groups):
    with pytest.raises(ValueError, match="Duplicate output target"):
        save_objects_to_json(groups, tmp_path)
    assert list(tmp_path.iterdir()) == []

@pytest.mark.parametrize("duplicate", [False, True])
def test_preflight_across_json_source_files(tmp_path, duplicate):
    from src.lib.transform.json_collections import build_collections_from_json

    source = tmp_path / "source"
    source.mkdir()
    for name, record in [("first", {"id": "same"}), ("second", {"id": "same"} if duplicate else {})]:
        (source / f"{name}.json").write_text(json.dumps([record]), encoding="utf-8")
        (source / f"{name}_organization_mapping.json").write_text(
            json.dumps({"mappings": [{"output_path": "id", "input_path": "id"}]}),
            encoding="utf-8",
        )
    # BLU-16 owns preservation of repeated types during searching_and_assigning.
    # Exercise all source groups supplied directly to the writer here.
    if not duplicate:
        (source / "second.json").write_text('[{"id": ""}]', encoding="utf-8")
    groups = build_collections_from_json(str(source))
    assert len(groups) == 2
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Duplicate output target" if duplicate else "Missing nonempty output ID"):
        save_objects_to_json(groups, output)
    assert not output.exists()
