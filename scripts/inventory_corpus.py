#!/usr/bin/env python3
"""Inventory the sample corpus under data/ (BLU-28 / P1-02a).

Collects FACTS ONLY about every data directory and ZIP archive:
source/mapping pairs, formats, columns, row counts, test references, and
what the current transformer *observably* does with each entry.

Rules this script follows:
  * No cell values from source data are written to the output, only column
    names, counts, hashes, and file names.
  * "observed" results are what the code did today. They are NOT approved
    expected results. Classification, permission, and reviewer fields are left
    as "unconfirmed" / null for the dataset steward to fill in.
  * Output is deterministic (no timestamps), so re-running at the same commit
    must produce an identical file.

Usage (from the repo root):
    uv run --locked --extra api --extra dev python scripts/inventory_corpus.py
    uv run --locked --extra api --extra dev python scripts/inventory_corpus.py --check
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TESTS = ROOT / "tests"
DEFAULT_OUT = ROOT / "docs" / "corpus" / "manifest.json"

sys.path.insert(0, str(ROOT))

# Same pattern the transformer uses (src/lib/transform/collections.py).
MAPPING_RE = re.compile(r"^(.+)_([A-Za-z0-9]+)_mapping\.(csv|json)$")
STANDARD_MAPPING_HEADER = ["path", "input_files_field"]

# Directories that are generated as a side effect of *running* this script
# (e.g. observe() dynamically imports a dataset's transforms.py, which makes
# Python write a __pycache__ next to it) rather than being part of the
# checked-in corpus. These must be excluded from enumeration, or the set of
# "subdirectories" recorded for a dataset depends on whether the script has
# already been run once in this checkout, breaking --check reproducibility.
IGNORED_SUBDIR_NAMES = {"__pycache__"}


def _is_inventoried_dir(name: str) -> bool:
    return name not in IGNORED_SUBDIR_NAMES and not name.startswith(".")

# Facts taken from the BLU-28 / BLU-14 ticket text, kept separate from anything
# the script measures. These are the ticket's claims, not conclusions.
TICKET_NOTES = {
    "HSD_example": ["ticket: layout mismatch; first mapping row consumed as a filter"],
    "simple_mapping": [
        "ticket: layout mismatch; reversed legacy column layout",
        "ticket: test_empty_input currently expects zero records from this dataset",
    ],
    "deprecated_hsds_mapping": ["ticket: mapping-only directory"],
    "wrongiCarol.zip": [
        "ticket: rejects a missing ResourceAgencyNum column; candidate negative case"
    ],
}


# --------------------------------------------------------------------------
# Low-level readers
# --------------------------------------------------------------------------
def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode(data: bytes) -> tuple[str, bool, bool]:
    """Return (text, has_bom, utf8_valid)."""
    bom = data.startswith(b"\xef\xbb\xbf")
    try:
        text = data.decode("utf-8")
        valid = True
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
        valid = False
    return text.lstrip("\ufeff"), bom, valid


def read_rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text, newline="")))


def source_csv_info(data: bytes) -> tuple[dict, list[list[str]]]:
    text, bom, valid = decode(data)
    info: dict = {
        "format": "csv",
        "bytes": len(data),
        "sha256": sha256(data),
        "bom": bom,
        "utf8_valid": valid,
    }
    try:
        rows = read_rows(text)
    except csv.Error as exc:
        info["parse_error"] = str(exc)[:200]
        return info, []
    header = rows[0] if rows else []
    body = rows[1:]
    nonblank = [r for r in body if any(c.strip() for c in r)]
    info.update(
        columns=header,
        column_count=len(header),
        data_rows=len(nonblank),
        blank_rows=len(body) - len(nonblank),
        rows_with_column_count_mismatch=sum(1 for r in nonblank if len(r) != len(header)),
        row_length_minus_header_length=dict(sorted(
            Counter(len(r) - len(header) for r in nonblank).items())),
    )
    return info, rows


def source_json_info(data: bytes) -> dict:
    text, bom, valid = decode(data)
    info: dict = {"format": "json", "bytes": len(data), "sha256": sha256(data), "bom": bom,
                  "utf8_valid": valid}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        info["parse_error"] = str(exc)[:200]
        return info
    if isinstance(obj, list):
        info.update(top_level="array", records=len(obj))
    elif isinstance(obj, dict):
        info.update(
            top_level="object",
            top_level_keys=sorted(obj)[:25],
            list_lengths={k: len(v) for k, v in obj.items() if isinstance(v, list)},
        )
    else:
        info["top_level"] = type(obj).__name__
    return info


def mapping_csv_info(data: bytes, source_rows: list[list[str]] | None) -> dict:
    """Describe a mapping CSV without interpreting it more than the parser does."""
    text, bom, valid = decode(data)
    info: dict = {"format": "csv", "bytes": len(data), "sha256": sha256(data), "bom": bom,
                  "utf8_valid": valid}
    try:
        rows = read_rows(text)
    except csv.Error as exc:
        info["parse_error"] = str(exc)[:200]
        return info
    header = [c.strip() for c in rows[0]] if rows else []
    row2 = rows[1] if len(rows) > 1 else []
    # Mirror parse_nested_mapping(): row 2 is a filter when both of its first
    # two cells are non-empty.
    f_col = (row2[0] if len(row2) > 0 else "").strip()
    f_val = (row2[1] if len(row2) > 1 else "").strip()
    filter_applied = bool(f_col and f_val)

    mapping_rows = []
    for r in rows[2:]:
        if len(r) < 2:
            continue
        out_path, in_field = (r[0] or "").strip(), (r[1] or "").strip()
        if out_path and in_field:
            mapping_rows.append((out_path, in_field))

    if header[:1] == ["path"]:
        layout = "path_first"
    elif header[1:2] == ["path"]:
        layout = "path_second"  # reversed legacy layout: input column first
    else:
        layout = "unrecognised"
    info.update(
        header_row=header,
        header_layout=layout,
        header_matches_template_exactly=header[:2] == STANDARD_MAPPING_HEADER,
        extra_header_columns=header[2:],
        mapping_row_count=len(mapping_rows),
        filter_row_interpreted_as_filter=filter_applied,
    )
    if filter_applied:
        info["filter_column"] = f_col

    referenced = sorted({f.strip() for _, fld in mapping_rows for f in fld.split(";") if f.strip()})
    info["referenced_input_field_count"] = len(referenced)

    if source_rows:
        src_header = source_rows[0]
        src_set = set(src_header)
        body = [r for r in source_rows[1:] if any(c.strip() for c in r)]
        info["referenced_fields_missing_from_source"] = [f for f in referenced if f not in src_set]
        col0 = {p for p, _ in mapping_rows}
        info["col0_values_found_in_source_columns"] = len(col0 & src_set)
        info["col1_values_found_in_source_columns"] = len(set(referenced) & src_set)
        if filter_applied:
            info["filter_column_in_source"] = f_col in src_set
            if f_col in src_set:
                i = src_header.index(f_col)
                # Same comparison as mapper.py: str(actual).strip() == str(value).strip()
                info["filter_matching_rows"] = sum(
                    1 for r in body if len(r) > i and r[i].strip() == f_val
                )
            else:
                info["filter_matching_rows"] = None
    return info


def mapping_json_info(data: bytes) -> dict:
    text, bom, valid = decode(data)
    info: dict = {"format": "json", "bytes": len(data), "sha256": sha256(data), "bom": bom,
                  "utf8_valid": valid}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        info["parse_error"] = str(exc)[:200]
        return info
    if isinstance(obj, dict):
        info["top_level_keys"] = sorted(obj)
        info["filter_present"] = bool(obj.get("filter"))
        if isinstance(obj.get("filter"), dict):
            info["filter_column"] = obj["filter"].get("column")
        if isinstance(obj.get("mappings"), list):
            info["mapping_row_count"] = len(obj["mappings"])
    return info


# --------------------------------------------------------------------------
# Entry builders (work on {relative_name: bytes} so dirs and ZIPs share logic)
# --------------------------------------------------------------------------
def analyse_files(files: dict[str, bytes]) -> dict:
    sources, mappings, other = {}, {}, []
    for name in sorted(files):
        m = MAPPING_RE.match(name)
        if m:
            mappings[name] = m
        elif name.endswith((".csv", ".json")):
            sources[name] = None
        else:
            other.append({"name": name, "bytes": len(files[name]), "sha256": sha256(files[name])})

    source_infos, source_rows = {}, {}
    for name in sources:
        if name.endswith(".csv"):
            source_infos[name], source_rows[name] = source_csv_info(files[name])
        else:
            source_infos[name] = source_json_info(files[name])

    mapping_infos = []
    for name, m in mappings.items():
        stem, obj_type, ext = m.groups()
        src_name = f"{stem}.{ext}"
        paired = src_name in sources
        info = (mapping_csv_info(files[name], source_rows.get(src_name))
                if ext == "csv" else mapping_json_info(files[name]))
        info.update(name=name, object_type=obj_type, expected_source=src_name,
                    source_found=paired)
        mapping_infos.append(info)

    paired_sources = {m["expected_source"] for m in mapping_infos if m["source_found"]}
    return {
        "source_files": [{"name": n, **source_infos[n]} for n in sources],
        "mapping_files": mapping_infos,
        "other_files": other,
        "sources_without_mapping": sorted(set(sources) - paired_sources),
        "mappings_without_source": sorted(m["name"] for m in mapping_infos if not m["source_found"]),
    }


def flags_for(analysis: dict, observed: dict) -> list[str]:
    flags = []
    if not analysis["source_files"] and analysis["mapping_files"]:
        flags.append("mapping_only")
    if analysis["mappings_without_source"] and analysis["source_files"]:
        flags.append("has_mapping_without_source")
    if analysis["sources_without_mapping"]:
        flags.append("has_source_without_mapping")
    for m in analysis["mapping_files"]:
        if m.get("format") == "csv" and m["source_found"]:
            if m.get("header_layout") != "path_first":
                flags.append("mapping_header_not_path_first")
            if (m.get("col0_values_found_in_source_columns", 0)
                    > m.get("col1_values_found_in_source_columns", 0)):
                flags.append("mapping_columns_possibly_reversed")
            if m.get("filter_row_interpreted_as_filter"):
                if m.get("filter_column_in_source") is False:
                    flags.append("filter_column_not_in_source")
                if not m.get("filter_matching_rows"):
                    flags.append("filter_matches_no_source_rows")
            if m.get("referenced_fields_missing_from_source"):
                flags.append("mapping_references_missing_source_columns")
    for s_ in analysis["source_files"]:
        deltas = {k for k in s_.get("row_length_minus_header_length", {}) if k != 0}
        if any(k > 0 for k in deltas):
            flags.append("rows_longer_than_header")
        if any(k < 0 for k in deltas):
            flags.append("rows_shorter_than_header")
    if observed.get("status") == "error":
        flags.append("observed_error")
    elif observed.get("status") == "ok" and observed.get("output_objects_after_linking") == 0:
        flags.append("observed_zero_output_objects")
    return sorted(set(flags))


# --------------------------------------------------------------------------
# Observed transformer behaviour (counts only; nothing is written to disk)
# --------------------------------------------------------------------------
def observe(directory: Path) -> dict:
    """Run the library the same way the CLI does and record counts only."""
    from src.lib.transform.collections import build_collections, searching_and_assigning
    from src.lib.transform.json_collections import build_collections_from_json
    from src.lib.transform.custom_transform.transforms_loader import (
        load_transforms_registry_if_available,
    )

    has_json_mapping = any(directory.glob("*_mapping.json"))
    has_csv_mapping = any(directory.glob("*_mapping.csv"))
    if not (has_json_mapping or has_csv_mapping):
        return {"status": "not_run", "reason": "no *_mapping.csv or *_mapping.json files"}

    transforms = directory / "transforms.py"
    registry = load_transforms_registry_if_available(transforms) if transforms.is_file() else None
    fmt = "json" if has_json_mapping and not has_csv_mapping else "csv"
    out: dict = {"status": "ok", "input_format": fmt,
                 "custom_transforms_used": registry is not None}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            if fmt == "json":
                results = build_collections_from_json(str(directory))
            else:
                results = build_collections(str(directory), custom_transforms_registry=registry)
            before = {name: len(objs) for name, objs in results}
            linked = searching_and_assigning(results)
        after = {name: len(objs) for name, objs in linked}
        distinct_ids = {
            name: len({str(o.get("id")) for o in objs if isinstance(o, dict) and o.get("id") is not None})
            for name, objs in linked
        }
        out.update(
            objects_before_linking=dict(sorted(before.items())),
            objects_before_linking_total=sum(before.values()),
            top_level_objects_after_linking=dict(sorted(after.items())),
            output_objects_after_linking=sum(after.values()),
            distinct_ids_after_linking=dict(sorted(distinct_ids.items())),
        )
    except Exception as exc:  # observing failures is part of the job
        out.update(status="error", error_type=type(exc).__name__,
                   error_message=str(exc)[:300])
    return out


# --------------------------------------------------------------------------
# Test references (path patterns only; no guessing from bare words)
# --------------------------------------------------------------------------
def find_test_references(name: str) -> list[dict]:
    base = re.escape(name)
    patterns = [
        rf"data[/\\]{base}(?!\w|\.zip)",
        rf"""DATA_DIR\s*/\s*["']{base}["']""",
        rf"""["']data["']\s*/\s*["']{base}["']""",
        rf"""["'](?:csv|json)["']\s*,\s*["']{base}["']""",
    ]
    rx = re.compile("|".join(patterns))
    refs = []
    candidates = sorted(TESTS.glob("*.py")) + [ROOT / "README.md"]
    for path in candidates:
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if rx.search(line):
                refs.append({"file": str(path.relative_to(ROOT)), "line": lineno})
    return refs


# --------------------------------------------------------------------------
# Main assembly
# --------------------------------------------------------------------------
def blank_review_fields() -> dict:
    return {
        "classification": "unconfirmed",  # supported | intentionally_invalid | legacy_reference_only | awaiting_permission
        "permission_status": "unconfirmed",
        "intended_purpose": "unconfirmed",
        "responsible_reviewer": None,
        "approved_expected_results": None,  # steward fills in; observed != approved
    }


def directory_entry(path: Path) -> dict:
    files = {p.name: p.read_bytes() for p in sorted(path.iterdir()) if p.is_file()}
    # Enumerate subdirectories before observe() runs: observe() dynamically
    # imports transforms.py (if present), which can cause Python to create a
    # __pycache__ directory here as a side effect. That cache is excluded via
    # _is_inventoried_dir() regardless of enumeration order, so the recorded
    # "subdirectories" list is identical whether or not the cache already
    # existed from a prior run.
    subdirs = sorted(
        p.name for p in path.iterdir() if p.is_dir() and _is_inventoried_dir(p.name)
    )
    analysis = analyse_files(files)
    observed = observe(path)
    entry = {
        "id": path.name,
        "kind": "directory",
        "path": f"data/{path.name}",
        **analysis,
        "subdirectories": subdirs,
        "observed": {"note": "observed behaviour at this commit; NOT an approved expected result",
                     **observed},
        "test_references": find_test_references(path.name),
        "flags": flags_for(analysis, observed),
        "ticket_notes": TICKET_NOTES.get(path.name, []),
        **blank_review_fields(),
    }
    return entry


def zip_entry(path: Path, directories: dict[str, dict[str, bytes]]) -> dict:
    with zipfile.ZipFile(path) as zf:
        bad = zf.testzip()
        members = {}
        for info in zf.infolist():
            if info.is_dir():
                continue
            parts = Path(info.filename).parts
            if info.filename.startswith("/") or ".." in parts:
                continue  # never trust odd paths
            members[info.filename] = zf.read(info)
    tops = sorted({Path(n).parts[0] for n in members if len(Path(n).parts) > 1})
    top = tops[0] if len(tops) == 1 and all(len(Path(n).parts) > 1 for n in members) else None
    flat = {(str(Path(n).relative_to(top)) if top else n): b for n, b in members.items()}
    analysis = analyse_files(flat)

    # Equivalence with the checked-in directory of the same top-level name
    equivalence: dict = {"compared_with": None}
    if top and top in directories:
        d = directories[top]
        crlf = lambda b: b.replace(b"\r\n", b"\n")  # noqa: E731
        differing = sorted(n for n in flat if n in d and flat[n] != d[n])
        equivalence = {
            "compared_with": f"data/{top}",
            "identical_files": sorted(n for n in flat if n in d and flat[n] == d[n]),
            "different_files": differing,
            "different_only_in_crlf_vs_lf": [n for n in differing if crlf(flat[n]) == crlf(d[n])],
            "different_beyond_line_endings": [n for n in differing if crlf(flat[n]) != crlf(d[n])],
            "only_in_zip": sorted(set(flat) - set(d)),
            "only_in_directory": sorted(set(d) - set(flat)),
        }
        diffs = {}
        for n in equivalence["different_files"]:
            if n.endswith(".csv"):
                za, _ = source_csv_info(flat[n])
                da, _ = source_csv_info(d[n])
                if "columns" in za and "columns" in da:
                    diffs[n] = {
                        "columns_missing_in_zip": [c for c in da["columns"] if c not in za["columns"]],
                        "columns_added_in_zip": [c for c in za["columns"] if c not in da["columns"]],
                        "data_rows_zip": za["data_rows"],
                        "data_rows_directory": da["data_rows"],
                    }
        if diffs:
            equivalence["csv_differences"] = diffs
        equivalence["fully_identical"] = (
            not equivalence["different_files"]
            and not equivalence["only_in_zip"]
            and not equivalence["only_in_directory"]
        )
        equivalent_modulo_line_endings = (
            not equivalence["different_beyond_line_endings"]
            and not equivalence["only_in_zip"]
            and not equivalence["only_in_directory"]
        )
        equivalence["equivalent_ignoring_line_endings"] = equivalent_modulo_line_endings

    with tempfile.TemporaryDirectory() as tmp:
        for rel, b in flat.items():
            dest = Path(tmp) / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b)
        observed = observe(Path(tmp))

    return {
        "id": path.name,
        "kind": "zip",
        "path": f"data/{path.name}",
        "zip_bytes": path.stat().st_size,
        "zip_sha256": sha256(path.read_bytes()),
        "zip_integrity_error_member": bad,
        "top_level_folder": top,
        **analysis,
        "directory_equivalence": equivalence,
        "observed": {"note": "observed behaviour at this commit; NOT an approved expected result",
                     **observed},
        "test_references": find_test_references(path.name),
        "flags": flags_for(analysis, observed),
        "ticket_notes": TICKET_NOTES.get(path.name, []),
        **blank_review_fields(),
    }


def similar_sources(dir_files: dict[str, dict[str, bytes]]) -> list[dict]:
    """Group directory CSV sources that share an identical column list and describe
    how they differ (column names + counts only; never cell values)."""
    groups: dict[tuple, list[tuple[str, str]]] = {}
    parsed: dict[tuple[str, str], list[list[str]]] = {}
    for d, files in dir_files.items():
        for name, data in files.items():
            if MAPPING_RE.match(name) or not name.endswith(".csv"):
                continue
            _, rows = source_csv_info(data)
            if len(rows) and len(rows[0]) >= 10:  # ignore tiny generic schemas
                groups.setdefault(tuple(rows[0]), []).append((d, name))
                parsed[(d, name)] = rows
    out = []
    for cols, members in groups.items():
        if len({d for d, _ in members}) < 2:
            continue
        base = members[0]
        item = {"identical_column_list": True, "column_count": len(cols),
                "reference": f"data/{base[0]}/{base[1]}", "others": []}
        for d, name in members[1:]:
            a, b = parsed[base][1:], parsed[(d, name)][1:]
            differing_cols = Counter()
            for ra, rb in zip(a, b):
                for c, va, vb in zip(cols, ra, rb):
                    if va != vb:
                        differing_cols[c] += 1
            item["others"].append({
                "path": f"data/{d}/{name}",
                "bytes_identical_to_reference": dir_files[base[0]][base[1]] == dir_files[d][name],
                "data_rows_reference": len(a),
                "data_rows_this": len(b),
                "cells_differing_by_column": dict(sorted(differing_cols.items())),
            })
            # mapping rows that differ (mapping rows are schema: output path + input column)
            ma = _paired_mapping_rows(dir_files[base[0]], base[1])
            mb = _paired_mapping_rows(dir_files[d], name)
            if ma is not None and mb is not None:
                diffs = [
                    {"file_line": i + 1, "reference": ra[:2], "this": rb[:2]}
                    for i, (ra, rb) in enumerate(zip(ma, mb)) if ra != rb
                ]
                other = item["others"][-1]
                other["mapping_row_count_reference_vs_this"] = [len(ma), len(mb)]
                other["mapping_rows_differing_count"] = len(diffs)
                if len(ma) == len(mb) and len(diffs) <= 5:
                    other["mapping_rows_differing"] = diffs  # schema rows only, no source values
        out.append(item)
    return out


def _paired_mapping_rows(files: dict[str, bytes], source_name: str):
    stem = source_name.rsplit(".", 1)[0]
    for n, b in files.items():
        m = MAPPING_RE.match(n)
        if m and m.group(1) == stem and n.endswith(".csv"):
            return read_rows(decode(b)[0])
    return None


def duplicate_files(dir_files: dict[str, dict[str, bytes]]) -> list[dict]:
    by_hash: dict[str, list[str]] = {}
    for d, files in sorted(dir_files.items()):
        for name, data in sorted(files.items()):
            by_hash.setdefault(sha256(data), []).append(f"data/{d}/{name}")
    return [{"sha256": h, "paths": paths} for h, paths in sorted(by_hash.items(), key=lambda kv: kv[1])
            if len(paths) > 1]


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def build_manifest() -> dict:
    dirs = sorted(p for p in DATA.iterdir() if p.is_dir() and _is_inventoried_dir(p.name))
    zips = sorted(p for p in DATA.iterdir() if p.is_file() and p.suffix == ".zip")
    dir_files = {d.name: {p.name: p.read_bytes() for p in d.iterdir() if p.is_file()} for d in dirs}
    entries = [directory_entry(d) for d in dirs] + [zip_entry(z, dir_files) for z in zips]
    return {
        "manifest_version": 1,
        "ticket": "BLU-28 (P1-02a)",
        "generated_from_commit": git_commit(),
        "generator": "scripts/inventory_corpus.py",
        "status_note": ("Facts only. 'observed' is current behaviour, not approved expectation. "
                        "classification/permission/reviewer fields are intentionally unconfirmed."),
        "counts": {"directories": len(dirs), "zip_archives": len(zips)},
        "byte_identical_files_across_directories": duplicate_files(dir_files),
        "similar_directory_sources": similar_sources(dir_files),
        "entries": entries,
    }


# Fields that record provenance about *when/where* the manifest was generated
# rather than facts about the corpus itself. These are expected to legitimately
# differ between two reproducible runs (e.g. generated on different commits
# with an unchanged corpus), so they're excluded from the --check comparison.
NON_REPRODUCIBLE_FIELDS = {"generated_from_commit"}


def _comparable(manifest: dict) -> dict:
    """Manifest dict with non-reproducible provenance fields stripped, for
    use when comparing two generations for corpus-level equality."""
    return {k: v for k, v in manifest.items() if k not in NON_REPRODUCIBLE_FIELDS}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true",
                    help="regenerate and fail if the file on disk differs (reproducibility check)")
    args = ap.parse_args()

    manifest = build_manifest()
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not args.out.exists():
            print(f"{args.out} does not exist; run without --check to generate it", file=sys.stderr)
            return 1
        try:
            current = json.loads(args.out.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"{args.out} is not valid JSON ({exc}); re-run without --check", file=sys.stderr)
            return 1
        # Compare both sides after an equivalent JSON round-trip (rather than
        # the freshly built `manifest` dict directly): JSON has no integer
        # keys, so e.g. row_length_minus_header_length's int keys become
        # strings once read back from disk. Parsing `text` the same way keeps
        # the comparison fair instead of spuriously failing on that asymmetry.
        new = json.loads(text)
        if _comparable(current) != _comparable(new):
            print(f"{args.out} is out of date; re-run without --check", file=sys.stderr)
            return 1
        print(f"{args.out} is up to date (ignoring provenance fields: "
              f"{', '.join(sorted(NON_REPRODUCIBLE_FIELDS))})")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())