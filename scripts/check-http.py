"""Startup/transport smoke with one known fixture; not a full corpus gate."""
import io
import json
from pathlib import Path
import sys
import zipfile

import requests

base = sys.argv[1]
health = requests.get(f"{base}/health", timeout=10)
assert health.status_code == 200
assert health.json()["status"] == "ok"
upload = io.BytesIO()
with zipfile.ZipFile(upload, "w") as archive:
    for path in sorted(Path("data/json_test").glob("*.json")):
        archive.write(path, path.name)
response = requests.post(
    f"{base}/transform", data={"input_format": "json"},
    files={"zip_file": ("input.zip", upload.getvalue(), "application/zip")}, timeout=60,
)
assert response.status_code == 201, (response.status_code, response.text[:500])
assert response.headers["content-type"] == "application/zip"
with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
    assert archive.testzip() is None
    organization = json.loads(archive.read("organization_1.json"))
assert organization["id"] == "1"
assert organization["name"] == "Test Organization"
print("Health and representative transformation passed")
