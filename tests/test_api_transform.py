import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import app


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
