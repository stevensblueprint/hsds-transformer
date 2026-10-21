"""Regression harness for cross-request transformer log accumulation.

The transformer pipeline writes to the module-level ``transformer_log``
singleton, so the API shares one log across every request. The request-state
refactor is owned by BLU-10; until it lands this test is a strict xfail so the
known leak stays visible without breaking default CI. When BLU-10 makes the
log request-owned, the test will XPASS and fail under ``strict=True``: remove
the marker and point the assertion at the new request-owned seam.

See docs/transformer-log-request-isolation.md.
"""

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from api.app import app
from lib.transform.logger import transformer_log

# Uppercase and hyphen never occur in tempfile's random names or pytest's
# tmp_path, so these markers can only reach the log via the uploaded filenames.
ALPHA = "REQ-ALPHA"
BETA = "REQ-BETA"

BLU_10 = "BLU-10: transformer_log is a process-wide singleton shared by all requests"

CSV_MAPPING = "path,input_files_field,split,strip\n,,,\nid,org_id,,\nname,org_name,,\n"
JSON_MAPPING = json.dumps(
    {
        "mappings": [
            {"output_path": "id", "input_path": "org_id"},
            {"output_path": "name", "input_path": "org_name"},
        ]
    }
)


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("HSDS_TMP_DIR", str(tmp_path))
    with TestClient(app) as client:
        yield client


def _post_transform(client, tag):
    """POST a one-organization CSV dataset whose filenames carry ``tag``."""
    upload = io.BytesIO()
    with zipfile.ZipFile(upload, "w") as archive:
        archive.writestr(f"{tag}_organization_mapping.csv", CSV_MAPPING)
        archive.writestr(f"{tag}.csv", f"org_id,org_name\n{tag}-1,{tag} org\n")
    return client.post(
        "/transform",
        files={"zip_file": ("input.zip", upload.getvalue(), "application/zip")},
    )


def _post_transform_stream(client, tag):
    """POST a one-organization JSON dataset whose filenames carry ``tag``."""
    records = json.dumps([{"org_id": f"{tag}-1", "org_name": f"{tag} org"}])
    return client.post(
        "/transform/stream",
        files=[
            ("files", (f"{tag}_organization_mapping.json", JSON_MAPPING, "application/json")),
            ("files", (f"{tag}.json", records, "application/json")),
        ],
    )


def _require(condition, message):
    if not condition:
        pytest.fail(message)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=BLU_10)
@pytest.mark.parametrize(
    "post", [_post_transform, _post_transform_stream], ids=["transform", "stream"]
)
def test_sequential_requests_do_not_share_transformer_log(client, post):
    # Two small requests that are distinguishable by input filename. Assertions
    # use these markers rather than absolute counts so the result does not
    # depend on what earlier tests left in the process. Preconditions use
    # pytest.fail so a broken request is a real failure, not the expected one.
    first = post(client, ALPHA)
    _require(first.status_code == 201, f"first request: {first.status_code} {first.text}")
    _require(any(ALPHA in entry for entry in transformer_log.entries), "first request not logged")

    second = post(client, BETA)
    _require(second.status_code == 201, f"second request: {second.status_code} {second.text}")
    second_log = list(transformer_log.entries)
    _require(any(BETA in entry for entry in second_log), "second request not logged")

    # Request-owned isolation: nothing the first request logged may be visible
    # in the log the second request produced.
    leaked = [entry for entry in second_log if ALPHA in entry]
    assert leaked == [], f"{len(leaked)} entries from the first request leaked: {leaked}"
