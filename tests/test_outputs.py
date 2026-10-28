import json
from pathlib import Path

import pytest

from src.lib.transform import outputs
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
    records = [record for object_type, items in groups for record in items
               if object_type == "organization"]
    assert len(records) == 2
    assert sum(record.get("id") == "same" for record in records) == (2 if duplicate else 1)
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Duplicate output target" if duplicate else "Missing nonempty output ID"):
        save_objects_to_json(groups, output)
    assert not output.exists()


@pytest.mark.parametrize("records", [[], [{"id": "new"}]])
@pytest.mark.parametrize("entry", ["organization_new.json", "unrelated.txt", ".hidden", "subdir"])
def test_nonempty_destination_refused_without_changes(tmp_path, records, entry):
    output = tmp_path / "output"
    output.mkdir()
    existing = output / entry
    if entry == "subdir":
        existing.mkdir()
    else:
        existing.write_bytes(b"keep exactly")
    with pytest.raises(ValueError, match="not empty.*No files were changed.*--output-dir"):
        save_objects_to_json([("organization", records)], output)
    assert list(output.iterdir()) == [existing]
    assert existing.is_dir() or existing.read_bytes() == b"keep exactly"
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("records", [[], [{"id": "one", "name": "Café"}, {"id": "two"}]])
def test_publication_counts_and_readback(tmp_path, existing, records):
    output = tmp_path / "output"
    if existing:
        output.mkdir()
    summary = save_objects_to_json([("organization", records)], output)
    assert summary.expected == summary.written == summary.verified == len(records)
    assert {p.name: json.loads(p.read_text(encoding="utf-8")) for p in output.iterdir()} == {
        f"organization_{record['id']}.json": record for record in records
    }
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize("bad_id", ["x/../../escape", r"x\..\escape", "x:y", "x\x00y"])
def test_unsafe_filename_last_creates_no_artifacts(tmp_path, bad_id):
    with pytest.raises(ValueError, match="Unsafe output filename.*record 2"):
        save_objects_to_json([("organization", [{"id": "ok"}, {"id": bad_id}])], tmp_path / "out")
    assert list(tmp_path.iterdir()) == []


def test_unsafe_object_type_creates_no_artifacts(tmp_path):
    with pytest.raises(ValueError, match="Unsafe output filename"):
        save_objects_to_json([("../organization", [{"id": "ok"}])], tmp_path / "out")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("failure", ["serialize", "write", "readback", "count", "publish"])
def test_late_failure_cleans_staging_and_publishes_nothing(tmp_path, monkeypatch, existing, failure):
    output = tmp_path / "out"
    if existing:
        output.mkdir()
    records = [{"id": "first"}, {"id": "last"}]
    if failure == "serialize":
        records[-1]["bad"] = object()
    elif failure in ("write", "readback", "count"):
        real_dump = outputs.json.dump

        def dump(record, stream, **kwargs):
            if record["id"] == "last":
                if failure == "write":
                    stream.write('{"partial":')
                    raise OSError("injected disk failure")
                if failure == "readback":
                    stream.write("{broken")
                    return
                (Path(stream.name).parent / "unexpected.json").write_text("{}")
            real_dump(record, stream, **kwargs)

        monkeypatch.setattr(outputs.json, "dump", dump)
    else:
        def rename(*args):
            raise OSError("injected publication failure")
        monkeypatch.setattr(Path, "rename", rename)
    with pytest.raises(ValueError if failure == "serialize" else OSError):
        save_objects_to_json([("organization", records)], output)
    assert output.exists() == existing
    assert list(tmp_path.iterdir()) == ([output] if existing else [])
    if existing:
        assert list(output.iterdir()) == []
    # Cleanup must permit a later retry after the failure is gone.
    monkeypatch.undo()
    save_objects_to_json([("organization", [{"id": "retry"}])], output)
    assert json.loads((output / "organization_retry.json").read_text()) == {"id": "retry"}


def test_destination_created_during_staging_is_preserved(tmp_path, monkeypatch):
    output = tmp_path / "out"
    real_verify = outputs._verify_outputs

    def verify(staging, names):
        count = real_verify(staging, names)
        output.mkdir()
        (output / "someone-elses.txt").write_bytes(b"keep")
        return count

    monkeypatch.setattr(outputs, "_verify_outputs", verify)
    with pytest.raises(ValueError, match="not empty"):
        save_objects_to_json([("organization", [{"id": "one"}])], output)
    assert list(tmp_path.iterdir()) == [output]
    assert [(p.name, p.read_bytes()) for p in output.iterdir()] == [("someone-elses.txt", b"keep")]


def test_overlapping_writer_refused_and_first_run_completes(tmp_path, monkeypatch):
    output = tmp_path / "out"
    real_verify = outputs._verify_outputs

    def verify(staging, names):
        with pytest.raises(ValueError, match="reserved by another run"):
            save_objects_to_json([("organization", [{"id": "second"}])], output)
        return real_verify(staging, names)

    monkeypatch.setattr(outputs, "_verify_outputs", verify)
    save_objects_to_json([("organization", [{"id": "first"}])], output)
    assert list(tmp_path.iterdir()) == [output]
    assert [p.name for p in output.iterdir()] == ["organization_first.json"]


def test_existing_file_destination_refused(tmp_path):
    output = tmp_path / "out"
    output.write_bytes(b"keep")
    with pytest.raises(ValueError, match="not a directory"):
        save_objects_to_json([], output)
    assert output.read_bytes() == b"keep"
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_non_json_number_refused(tmp_path, value):
    with pytest.raises(ValueError, match="Could not serialize"):
        save_objects_to_json([("organization", [{"id": "one", "value": value}])], tmp_path / "out")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("fmt,dataset", [("csv", "iCarol"), ("json", "json_test")])
def test_cli_sample_output_and_repeat_refusal(tmp_path, fmt, dataset):
    from click.testing import CliRunner
    from src.cli.main import main

    source = Path(__file__).resolve().parents[1] / "data" / dataset
    output = tmp_path / "out"
    args = [str(source), "-f", fmt, "-o", str(output)]
    first = CliRunner().invoke(main, args)
    assert first.exit_code == 0, first.output
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert before
    assert all(json.loads(content)["id"] for content in before.values())
    assert f"expected={len(before)}, written={len(before)}, verified={len(before)}" in first.output
    second = CliRunner().invoke(main, args)
    assert second.exit_code == 1
    assert "not empty" in second.output and "--output-dir" in second.output
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    assert list(tmp_path.iterdir()) == [output]
