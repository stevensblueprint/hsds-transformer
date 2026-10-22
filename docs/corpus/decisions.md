# BLU-28 — Corpus inventory: findings and decisions for the dataset steward

**Scope:** facts only. Nothing here approves data reuse, classifies an entry as supported, repairs a mapping, or treats an observed output as correct.

- Manifest: [`manifest.json`](manifest.json), generated from commit `242b283` by `scripts/inventory_corpus.py`.
- Reproduce: `uv run --locked --extra api --extra dev python scripts/inventory_corpus.py` (add `--check` to confirm the committed manifest is current).
- No source cell values are written to the manifest or this document: only file names, column names, counts, and hashes.
- Every entry has `classification`, `permission_status`, and `intended_purpose` set to `unconfirmed`, and `responsible_reviewer` and `approved_expected_results` left `null`.

## Inventory at a glance

"Observed objects" is the top-level object count after linking, as the current code produces it. It is **not** an approved expected result.

| Entry | Kind | Sources / mappings | Source rows | Observed objects | Referenced by | Automatic flags |
|---|---|---|---|---|---|---|
| `HSD_example` | directory | 1 / 1 | 2592 | 0 | none | `filter_column_not_in_source`, `filter_matches_no_source_rows`, `observed_zero_output_objects`, `rows_longer_than_header` |
| `custom_transform_manual_test` | directory | 1 / 1 | 2 | 2 | none | none |
| `deprecated_hsds` | directory | 5 / 5 | 38 | 12 | none | none |
| `deprecated_hsds_mapping` | directory | 0 / 4 | 0 | 0 | none | `mapping_only`, `observed_zero_output_objects` |
| `florida_data` | directory | 3 / 3 | 533 | 155 | none | none |
| `iCarol` | directory | 1 / 1 | 20 | 2 | test_api_transform.py, test_transformer.py | none |
| `iCarol2` | directory | 1 / 1 | 20 | 2 | none | none |
| `iCarol3` | directory | 1 / 1 | 20 | 2 | none | none |
| `json_test` | directory | 1 / 1 | 1 | 1 | test_api_transform.py, test_json_collections.py | none |
| `logger_test` | directory | 2 / 2 | 5 | 2 | test_transformer.py | none |
| `sal_example` | directory | 4 / 4 | 46 | 10 | none | none |
| `sanity_check` | directory | 3 / 3 | 4 | 1 | README.md, test_sanity_check.py, test_transformer.py | none |
| `services` | directory | 1 / 1 | 13 | 13 | none | none |
| `simple_mapping` | directory | 1 / 1 | 10 | 0 | test_transformer.py | `filter_column_not_in_source`, `filter_matches_no_source_rows`, `mapping_header_not_path_first`, `observed_zero_output_objects` |
| `split_test` | directory | 1 / 1 | 7 | 7 | test_sanity_check.py, test_transformer.py | none |
| `transform_test` | directory | 1 / 1 | 1 | 1 | test_custom_transform.py | none |
| `visionlink` | directory | 2 / 2 | 14 | 3 | none | none |
| `wellskydata` | directory | 5 / 5 | 78 | 10 | none | none |
| `sal_example.zip` | zip | 4 / 4 | 46 | 10 | README.md | none |
| `visionlink.zip` | zip | 2 / 2 | 14 | 3 | none | none |
| `wellskydata.zip` | zip | 5 / 5 | 78 | 10 | none | none |
| `wrongiCarol.zip` | zip | 1 / 1 | 20 | error | none | `filter_matches_no_source_rows`, `mapping_references_missing_source_columns`, `observed_error`, `rows_longer_than_header` |

## Triage by evidence (not a classification)

- **Referenced by existing tests, so likely fixture candidates:** `iCarol`, `json_test`, `logger_test`, `sanity_check`, `split_test`, `transform_test` (uses custom transforms), plus `simple_mapping` (referenced as a zero-output case).
- **Run without error, no test reference:** `custom_transform_manual_test`, `deprecated_hsds`, `florida_data`, `iCarol2`, `iCarol3`, `sal_example`, `services`, `visionlink`, `wellskydata`, and the `sal_example`, `visionlink`, and `wellskydata` ZIPs. `sal_example.zip` appears only in README examples.
- **Observed problems or ticket-named oddities:** `HSD_example`, `simple_mapping`, `deprecated_hsds_mapping`, `wrongiCarol.zip`.

## Decisions needed

1. **Permission and provenance (all entries).** No file in `data/` states where the data came from or whether it may be reused. Which entries may stay in the repo and serve as regression fixtures, and who is the responsible reviewer for each? Several sources are large or look like operational exports (`HSD_example` 2,592 rows, `wellskydata`, `visionlink`, `florida_data`).
2. **Classification.** Assign each entry: supported, intentionally invalid, legacy/reference-only, or awaiting permission.
3. **`HSD_example`.** The mapping header is standard, but row 2 (the first real mapping row) is read as a filter on a column that does not exist in the source, so 0 objects result. Separately, all 2,592 source rows have one more cell than the 29-column header. *Note:* the ticket cites the mapping file for "2,592 rows"; that count belongs to the source `HSD_provider.csv` (the mapping has 9 usable rows). Repair or retire?
4. **`simple_mapping`.** The mapping header is `input_file_col,path` (reversed), and row 2 is read as a filter on a missing column, so 0 objects result. `test_empty_input` (`tests/test_transformer.py:33`) currently asserts that empty result, so repairing the mapping would require changing that test. Repair or retire?
5. **`deprecated_hsds_mapping`.** It has four mappings and no sources. All four are byte-identical to mappings in `deprecated_hsds` (`phones_phone_mapping.csv` matches both phone mappings there). Is it intended as a template or reference, or should it be retired?
6. **`wrongiCarol.zip` as a named negative fixture.** It fails with `Invalid mapping: ... ResourceAgencyNum`. Beyond that, its source header has 168 columns while all 20 rows have 169 cells. The missing column was the first one in `iCarol`, so every header name sits one position left of its values, and the mapping's filter matches 0 rows (it matches 2 in `iCarol`). Is this meant to be a single-cause negative case, or should a minimal one be built?
7. **`iCarol` / `iCarol2` / `iCarol3`.** All three have the same 169-column header and 20 rows. `iCarol2` and `iCarol3` have byte-identical mappings that differ from `iCarol` in two rows (phone number and description fields map `Phone1`–`Phone3`), and five phone columns (`Phone2Name`, `Phone2Number`, and `Phone3`–`Phone5Number`) differ from `iCarol` in up to 12 of the 20 rows. Only `iCarol` is referenced by tests. What are the variants for, and are they needed?
8. **Duplicated files.** Several files are byte-identical across directories (for example `deprecated_hsds/organizations.csv`, `sal_example/salorganizations.csv`, and `simple_mapping/organizations.csv`; the full list is under `byte_identical_files_across_directories`). Which copy is canonical, and should shared fixtures be consolidated?
9. **ZIP vs. directory equivalence.** `sal_example.zip`, `visionlink.zip`, and `wellskydata.zip` match their directories only after normalizing line endings (the ZIP mappings use CRLF). Some CSV cells contain embedded line breaks, so parsed values in three source files differ by `\r\n` vs `\n`. Which form is canonical, and does that difference matter for expected results?
10. **Expected results.** For any entry judged supported, someone independent of this inventory must review object counts, distinct identities, relationship edges, intentional filters, and rejected-record expectations. The observed counts above are a starting point only.
11. **Documentation drift (low priority).** `CLAUDE.md` places modules at `src/lib/*.py`, but they live in `src/lib/transform/`, and it says no test framework exists, whereas 68 tests currently pass (the ticket's audit counted 67). `custom_transform_manual_test` has no test references and its name suggests manual use; confirm whether it should stay.

## Baseline observed while collecting this

At `242b283`, Python 3.13: `pytest tests/ -q` reported 68 passed. Docker was not exercised.