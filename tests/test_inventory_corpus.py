"""Regression tests for scripts/inventory_corpus.py reproducibility.

Four bugs motivated these tests (see BLU-28 review):

1. ``generated_from_commit`` recorded the git HEAD at generation time and was
   part of the ``--check`` byte-for-byte comparison, so an unchanged corpus
   failed ``--check`` on any checkout whose HEAD differed from the commit the
   manifest was generated on.
2. ``directory_entry()`` enumerated subdirectories before ``observe()`` ran.
   ``observe()`` dynamically imports a dataset's ``transforms.py`` (if any),
   which causes Python to write a ``__pycache__`` directory next to it. A
   manifest generated before that cache existed, re-checked after it exists
   (or vice versa), would disagree about a dataset's "subdirectories" even
   though nothing about the corpus itself had changed.
3. ``find_test_references()`` recorded ``str(path)``, so test file paths used
   backslashes on Windows and forward slashes elsewhere, and ``--check``
   failed across platforms with unchanged inputs.
4. ``build_manifest()`` sorted ``Path`` objects, which compare
   case-insensitively on Windows only, so entry order differed by platform.

These tests build a minimal synthetic corpus in a temp directory (pointing
the script's module-level ROOT/DATA/TESTS/DEFAULT_OUT constants at it) so
they don't depend on, or mutate, the real data/ corpus.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

inventory_corpus = importlib.import_module("scripts.inventory_corpus")


def _make_corpus(data_dir: Path) -> None:
    """A tiny dataset with no *_mapping.csv/json file, so observe() takes the
    cheap 'not_run' path and we don't need to exercise the full transform
    pipeline just to test manifest reproducibility."""
    dataset = data_dir / "sample_dataset"
    dataset.mkdir(parents=True)
    (dataset / "people.csv").write_text("name,age\nAda,36\n", encoding="utf-8")


@pytest.fixture
def corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Point the script at an isolated, temporary corpus/output location."""
    data_dir = tmp_path / "data"
    tests_dir = tmp_path / "tests"
    out_path = tmp_path / "docs" / "corpus" / "manifest.json"
    data_dir.mkdir()
    tests_dir.mkdir()

    _make_corpus(data_dir)

    monkeypatch.setattr(inventory_corpus, "ROOT", tmp_path)
    monkeypatch.setattr(inventory_corpus, "DATA", data_dir)
    monkeypatch.setattr(inventory_corpus, "TESTS", tests_dir)
    monkeypatch.setattr(inventory_corpus, "DEFAULT_OUT", out_path)

    return {"data": data_dir, "out": out_path}


def _run_with_args(args: list[str]) -> int:
    import sys

    old_argv = sys.argv
    sys.argv = ["inventory_corpus.py", *args]
    try:
        return inventory_corpus.main()
    finally:
        sys.argv = old_argv


def test_check_passes_with_unchanged_inputs_run_twice(corpus, monkeypatch):
    """Baseline: generating, then checking with truly nothing different,
    must succeed."""
    monkeypatch.setattr(inventory_corpus, "git_commit", lambda: "a" * 40)

    assert _run_with_args([]) == 0
    assert _run_with_args(["--check"]) == 0
    assert _run_with_args(["--check"]) == 0


def test_check_passes_across_different_commit_hashes(corpus, monkeypatch):
    """Regression for bug 1: --check must not fail just because HEAD moved,
    as long as the corpus itself is unchanged."""
    monkeypatch.setattr(inventory_corpus, "git_commit", lambda: "1" * 40)
    assert _run_with_args([]) == 0

    # Simulate checking out a later, unrelated commit with the same corpus.
    monkeypatch.setattr(inventory_corpus, "git_commit", lambda: "2" * 40)
    assert _run_with_args(["--check"]) == 0


def test_check_passes_when_pycache_appears_between_runs(corpus, monkeypatch):
    """Regression for bug 2: a __pycache__ directory materializing inside a
    dataset directory between generation and --check (e.g. because observe()
    imported that dataset's transforms.py) must not be treated as a change."""
    monkeypatch.setattr(inventory_corpus, "git_commit", lambda: "a" * 40)

    assert _run_with_args([]) == 0
    assert _run_with_args(["--check"]) == 0

    pycache = corpus["data"] / "sample_dataset" / "__pycache__"
    pycache.mkdir()
    (pycache / "transforms.cpython-313.pyc").write_bytes(b"\x00\x01\x02")
    # A cache at the top of data/ must not be inventoried as a dataset either.
    (corpus["data"] / "__pycache__").mkdir()

    assert _run_with_args(["--check"]) == 0

    manifest = json.loads(corpus["out"].read_text(encoding="utf-8"))
    entry = next(e for e in manifest["entries"] if e["id"] == "sample_dataset")
    assert entry["subdirectories"] == []


def test_test_reference_paths_use_forward_slashes(corpus, monkeypatch):
    """Regression for bug 3: test_references recorded str(path), so a manifest
    generated on Windows had backslashes and --check failed on Linux/macOS with
    unchanged inputs."""
    monkeypatch.setattr(inventory_corpus, "git_commit", lambda: "a" * 40)
    tests_dir = inventory_corpus.TESTS
    (tests_dir / "test_sample.py").write_text(
        'DATASET = "data/sample_dataset"\n', encoding="utf-8"
    )

    assert _run_with_args([]) == 0
    assert _run_with_args(["--check"]) == 0
    assert _run_with_args(["--check"]) == 0

    manifest = json.loads(corpus["out"].read_text(encoding="utf-8"))
    entry = next(e for e in manifest["entries"] if e["id"] == "sample_dataset")
    assert entry["test_references"] == [{"file": "tests/test_sample.py", "line": 1}]


def test_entry_order_is_case_sensitive_on_every_platform(corpus, monkeypatch):
    """Regression for bug 4: sorting Path objects is case-insensitive on
    Windows only, so entry order differed between platforms."""
    monkeypatch.setattr(inventory_corpus, "git_commit", lambda: "a" * 40)
    for name in ("alpha", "Zeta"):
        (corpus["data"] / name).mkdir()
        (corpus["data"] / name / "people.csv").write_text("name\nAda\n", encoding="utf-8")

    assert _run_with_args([]) == 0

    manifest = json.loads(corpus["out"].read_text(encoding="utf-8"))
    assert [e["id"] for e in manifest["entries"]] == ["Zeta", "alpha", "sample_dataset"]


def test_committed_manifest_has_no_os_specific_paths():
    """The checked-in manifest must not depend on the OS it was generated on."""
    manifest_path = Path(inventory_corpus.__file__).resolve().parents[1] / "docs" / "corpus" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = [ref["file"] for e in manifest["entries"] for ref in e["test_references"]]
    assert files
    assert not [f for f in files if "\\" in f]


def test_check_still_catches_real_corpus_changes(corpus, monkeypatch):
    """Guard against the fix being so permissive that --check stops catching
    genuine drift."""
    monkeypatch.setattr(inventory_corpus, "git_commit", lambda: "a" * 40)
    assert _run_with_args([]) == 0

    (corpus["data"] / "sample_dataset" / "people.csv").write_text(
        "name,age\nAda,36\nGrace,85\n", encoding="utf-8"
    )

    assert _run_with_args(["--check"]) == 1
