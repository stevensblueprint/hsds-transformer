"""Check the installed distribution from a temporary working directory."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import src
from fastapi.testclient import TestClient
from src.api.app import app

root = Path(sys.argv[1]).resolve()
assert not Path(src.__file__).resolve().is_relative_to(root), src.__file__
with TestClient(app) as client:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
with tempfile.TemporaryDirectory() as output:
    subprocess.run([
        sys.executable, "-m", "src.cli.main", str(root / "data/json_test"),
        "-f", "json", "-o", output,
    ], check=True)
    organization = json.loads((Path(output) / "organization_1.json").read_text())
    assert organization["id"] == "1"
    assert organization["name"] == "Test Organization"
