import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import app

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("HSDS_TMP_DIR", str(tmp_path))
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    "endpoint,input_format,dataset,organization_id,organization_name",
    [
        ("/transform", "csv", "iCarol", "87138316",
         "Woda Cooper Companies - Cumberland Meadows"),
        ("/transform", "json", "json_test", "1", "Test Organization"),
        ("/transform/stream", "json", "json_test", "1", "Test Organization"),
    ],
)
def test_transform_created_zip(
    client, endpoint, input_format, dataset, organization_id, organization_name
):
    paths = sorted((DATA_DIR / dataset).glob(f"*.{input_format}"))
    assert paths
    if endpoint == "/transform":
        upload = io.BytesIO()
        with zipfile.ZipFile(upload, "w") as archive:
            for path in paths:
                archive.writestr(path.name, path.read_bytes())
        response = client.post(
            endpoint,
            data={"input_format": input_format},
            files={"zip_file": ("input.zip", upload.getvalue(), "application/zip")},
        )
    else:
        response = client.post(
            endpoint,
            files=[
                ("files", (path.name, path.read_bytes(), "application/json"))
                for path in paths
            ],
        )

    assert response.status_code == 201
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == (
        "attachment; filename=transformed.zip"
    )
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.testzip() is None
        organization = json.loads(archive.read(f"organization_{organization_id}.json"))
    assert organization["id"] == organization_id
    assert organization["name"] == organization_name


@pytest.mark.parametrize("endpoint", ["/transform", "/transform/stream"])
def test_transform_openapi_success_status(client, endpoint):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    responses = response.json()["paths"][endpoint]["post"]["responses"]
    assert "201" in responses
    assert "200" not in responses


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize("input_format", ["csv", "json"])
def test_api_rejects_unavailable_transform_without_importing_upload(client, input_format, tmp_path):
    sentinel = tmp_path / "executed.txt"
    script = f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('executed')\ntransforms = {{'uppercase': str.upper}}"
    if input_format == "json":
        source = json.dumps([{"id": "org-1", "name": "hello"}])
        mapping = json.dumps({"mappings": [
            {"output_path": "name", "input_path": "name", "transform": "uppercase"}
        ]})
    else:
        source = "id,name\norg-1,hello\n"
        mapping = "path,input_field,split,strip,transform\n,,,,\nname,name,,,uppercase\n"
    upload = io.BytesIO()
    with zipfile.ZipFile(upload, "w") as archive:
        archive.writestr(f"organizations.{input_format}", source)
        archive.writestr(f"organizations_organization_mapping.{input_format}", mapping)
        archive.writestr("transforms.py", script)
    response = client.post("/transform", data={"input_format": input_format},
        files={"zip_file": ("input.zip", upload.getvalue(), "application/zip")})
    assert response.status_code == 422
    assert "uppercase" in response.json()["detail"]
    assert not sentinel.exists()


@pytest.mark.parametrize("endpoint,input_format", [
    ("/transform", "csv"), ("/transform", "json"), ("/transform/stream", "json"),
])
@pytest.mark.parametrize("duplicate", [False, True])
def test_output_identity_errors_return_422(client, tmp_path, endpoint, input_format, duplicate):
    second_id = "same" if duplicate else ""
    if input_format == "json":
        source = json.dumps([{"id": "same"}, {"id": second_id}])
        mapping = json.dumps({"mappings": [{"output_path": "id", "input_path": "id"}]})
    else:
        source = f"id,name\nsame,First\n{second_id},Second\n"
        mapping = "path,input_field,split,strip,transform\n,,,,\nid,id,,,\n"
    files = {
        f"organizations.{input_format}": source,
        f"organizations_organization_mapping.{input_format}": mapping,
    }
    if endpoint == "/transform":
        upload = io.BytesIO()
        with zipfile.ZipFile(upload, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        response = client.post(endpoint, data={"input_format": input_format},
            files={"zip_file": ("input.zip", upload.getvalue(), "application/zip")})
    else:
        response = client.post(endpoint, files=[
            ("files", (name, content, "application/json")) for name, content in files.items()
        ])
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert ("Duplicate output target" if duplicate else "Missing nonempty output ID") in detail
    assert "organization" in detail
    assert "record 2" in detail
    assert "content-disposition" not in response.headers
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("endpoint", ["/transform", "/transform/stream"])
@pytest.mark.parametrize("failure", [None, "write", "readback"])
def test_output_publication_requests_cleanup_and_retry(tmp_path, monkeypatch, endpoint, failure):
    from lib.transform import outputs

    monkeypatch.setenv("HSDS_TMP_DIR", str(tmp_path))
    paths = sorted((DATA_DIR / "json_test").glob("*.json"))
    contents = {path.name: path.read_bytes() for path in paths}
    records = json.loads(contents["orgs.json"])
    records.append({**records[0], "ID": "2"})
    contents["orgs.json"] = json.dumps(records).encode("utf-8")
    if endpoint == "/transform":
        upload = io.BytesIO()
        with zipfile.ZipFile(upload, "w") as archive:
            for name, content in contents.items():
                archive.writestr(name, content)
        kwargs = {
            "data": {"input_format": "json"},
            "files": {"zip_file": ("input.zip", upload.getvalue(), "application/zip")},
        }
    else:
        kwargs = {"files": [
            ("files", (name, content, "application/json")) for name, content in contents.items()
        ]}
    real_dump = outputs.json.dump
    writes = 0

    def dump(record, stream, **options):
        nonlocal writes
        writes += 1
        if writes == 2 and failure:
            if failure == "write":
                raise OSError("injected disk failure")
            stream.write("{broken")
            return
        real_dump(record, stream, **options)

    with TestClient(app, raise_server_exceptions=False) as client:
        with monkeypatch.context() as patch:
            patch.setattr(outputs.json, "dump", dump)
            response = client.post(endpoint, **kwargs)
        assert response.status_code == (500 if failure else 201)
        assert list(tmp_path.iterdir()) == []
        # Fresh requests succeed after both ordinary success and failed publication.
        response = client.post(endpoint, **kwargs)
        assert response.status_code == 201
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert set(archive.namelist()) == {"organization_1.json", "organization_2.json"}
            assert json.loads(archive.read("organization_1.json"))["name"] == "Test Organization"
            assert all(json.loads(archive.read(name))["id"] for name in archive.namelist())
        assert list(tmp_path.iterdir()) == []
