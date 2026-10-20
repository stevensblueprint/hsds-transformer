import importlib
import io
import zipfile
from types import SimpleNamespace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

api = importlib.import_module("api.app")


def archive_bytes(entries, compression=zipfile.ZIP_STORED):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return buffer.getvalue()


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("HSDS_TMP_DIR", str(tmp_path))
    with TestClient(api.app) as client:
        yield client


def post(client, content):
    return client.post("/transform", files={"zip_file": ("input.zip", content, "application/zip")})


@pytest.mark.parametrize("field,value,entries,compression,detail", [
    ("max_members", 1, [("a", b"a"), ("folder/", b"")], zipfile.ZIP_STORED, "members"),
    ("max_file_bytes", 3, [("a", b"abcd")], zipfile.ZIP_STORED, "file"),
    ("max_total_bytes", 3, [("a", b"ab"), ("b", b"cd")], zipfile.ZIP_STORED, "total"),
    ("max_ratio", 2, [("a", b"a" * 128)], zipfile.ZIP_DEFLATED, "ratio"),
])
def test_zip_metadata_budgets(client, monkeypatch, tmp_path, field, value, entries, compression, detail):
    limits = dict(max_members=10, max_file_bytes=1024, max_total_bytes=2048, max_ratio=100)
    limits[field] = value
    monkeypatch.setattr(api, "ZIP_LIMITS", SimpleNamespace(**limits), raising=False)
    response = post(client, archive_bytes(entries, compression))
    assert response.status_code == 413
    assert detail in response.json()["detail"]
    assert "content-disposition" not in response.headers
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("name", ["../outside", "folder/../../outside", "/absolute", "C:/outside", "folder\\outside"])
def test_unsafe_names_rejected(client, tmp_path, name):
    response = post(client, archive_bytes([(name, b"tiny")]))
    assert response.status_code == 422
    assert "path" in response.json()["detail"]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ["encrypted", "unsupported", "symlink", "crc", "collision", "directory_data"])
def test_invalid_entries_rejected_and_cleaned(client, tmp_path, kind):
    import stat
    import struct

    entries = [("first", b"ok"), ("second", b"tiny")]
    if kind == "collision":
        entries = [("folder", b"ok"), ("folder/child", b"tiny")]
    elif kind == "directory_data":
        entries = [("folder/", b"tiny")]
    elif kind == "symlink":
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        entries = [(info, b"../outside")]
    content = bytearray(archive_bytes(entries))
    if kind in ("encrypted", "unsupported"):
        local = content.rfind(b"PK\x03\x04")
        central = content.rfind(b"PK\x01\x02")
        offsets = (local + 6, central + 8) if kind == "encrypted" else (local + 8, central + 10)
        for offset in offsets:
            struct.pack_into("<H", content, offset, 1 if kind == "encrypted" else 99)
    elif kind == "crc":
        offset = content.index(b"tiny")
        content[offset] = ord("X")
    response = post(client, bytes(content))
    assert response.status_code == 422
    assert "content-disposition" not in response.headers
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("field,value,detail", [
    ("max_file_bytes", 3, "file"),
    ("max_total_bytes", 4, "total"),
    ("max_ratio", 2, "ratio"),
])
def test_actual_stream_budgets(client, monkeypatch, tmp_path, field, value, detail):
    # Substitute a tiny stream at the ZIP I/O boundary to prove actual bytes
    # are checked independently of trusted-looking metadata. No bomb fixture.
    original_open = zipfile.ZipFile.open
    def open_stream(self, name, mode="r", *args, **kwargs):
        if mode == "r" and isinstance(name, zipfile.ZipInfo) and name.filename == "second":
            return io.BytesIO(b"abcd")
        return original_open(self, name, mode, *args, **kwargs)

    limits = dict(max_members=10, max_file_bytes=100, max_total_bytes=100, max_ratio=100)
    limits[field] = value
    monkeypatch.setattr(api, "ZIP_LIMITS", SimpleNamespace(**limits))
    monkeypatch.setattr(zipfile.ZipFile, "open", open_stream)
    response = post(client, archive_bytes([("first", b"ab"), ("second", b"x")]))
    assert response.status_code == 413
    assert detail in response.json()["detail"]
    assert list(tmp_path.iterdir()) == []


def test_nested_valid_upload_preserves_records_and_cleans_workspace(client, tmp_path):
    import json
    dataset = Path(__file__).resolve().parents[1] / "data" / "json_test"
    entries = [("dataset/", b"")] + [(f"dataset/{p.name}", p.read_bytes()) for p in sorted(dataset.glob("*.json"))]
    response = client.post("/transform", data={"input_format": "json"},
        files={"zip_file": ("input.zip", archive_bytes(entries, zipfile.ZIP_DEFLATED), "application/zip")})
    assert response.status_code == 201
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        organization = json.loads(archive.read("organization_1.json"))
        assert organization["id"] == "1"
        assert organization["name"] == "Test Organization"
    assert list(tmp_path.iterdir()) == []


def test_exact_budget_boundary(tmp_path):
    from api.zip_upload import ZipLimits, extract_zip
    with zipfile.ZipFile(io.BytesIO(archive_bytes([("a", b"abcd")]))) as archive:
        extract_zip(archive, tmp_path, ZipLimits(
            max_members=1, max_file_bytes=4, max_total_bytes=4, max_ratio=1))
    assert (tmp_path / "a").read_bytes() == b"abcd"


def test_duplicate_basename_still_rejected(client, tmp_path):
    response = post(client, archive_bytes([("a/source.csv", b"a"), ("b/source.csv", b"b")]))
    assert response.status_code == 422
    assert "Duplicate filename" in response.json()["detail"]
    assert list(tmp_path.iterdir()) == []


def test_actual_byte_limit_is_checked_before_write(monkeypatch, tmp_path):
    from api.zip_upload import ZipLimits, extract_zip
    from fastapi import HTTPException

    with zipfile.ZipFile(io.BytesIO(archive_bytes([("a", b"x")]))) as archive:
        monkeypatch.setattr(archive, "open", lambda *_: io.BytesIO(b"abcd"))
        with pytest.raises(HTTPException) as error:
            extract_zip(archive, tmp_path, ZipLimits(max_file_bytes=3))
    assert error.value.status_code == 413
    assert (tmp_path / "a").read_bytes() == b""


def test_overlong_member_path_rejected_without_echoing_input(client, tmp_path):
    response = post(client, archive_bytes([("x" * 256, b"a")]))
    assert response.status_code == 422
    assert response.json()["detail"] == "Zip member path is too long; shorten folder and file names"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("header", ["version", "central_utf8", "local_utf8"])
def test_malformed_zip_headers_rejected_and_cleaned(client, tmp_path, header):
    import struct

    content = bytearray(archive_bytes([("a.csv", b"a,b\n1")]))
    central = content.index(b"PK\x01\x02")
    if header == "version":
        struct.pack_into("<H", content, central + 6, 100)
    else:
        flags, filename = (central + 8, central + 46) if header == "central_utf8" else (6, 30)
        struct.pack_into("<H", content, flags, 0x800)
        content[filename] = 0xff
    response = post(client, bytes(content))
    assert response.status_code == 422
    assert response.json()["detail"] in (
        "Invalid zip file", "Invalid or unsupported zip entry; recreate the zip"
    )
    assert "content-disposition" not in response.headers
    assert list(tmp_path.iterdir()) == []
