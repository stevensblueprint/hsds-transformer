"""Check an explicitly selected running API; this does not certify a release."""

import argparse
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx


DATA = Path(__file__).resolve().parents[1] / "data"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_archive(response, organization_id, organization_name):
    require(response.status_code == 201, f"Expected 201, got {response.status_code}")
    require(response.headers.get("content-type") == "application/zip", "Expected ZIP content type")
    require(
        response.headers.get("content-disposition") == "attachment; filename=transformed.zip",
        "Expected download filename",
    )
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        require(archive.testzip() is None, "ZIP integrity failure")
        record = json.loads(archive.read(f"organization_{organization_id}.json"))
    require(record["id"] == organization_id, "Unexpected organization ID")
    require(record["name"] == organization_name, "Unexpected organization name")


def run(base_url):
    # No redirects: a login page or redirect must not look like API success.
    with httpx.Client(base_url=base_url.rstrip("/") + "/", timeout=30) as client:
        response = client.get("health")
        require(response.status_code == 200, f"Health returned {response.status_code}")
        require(response.json()["status"] == "ok", "Health status is not ok")
        require(response.headers.get("cache-control") == "no-store", "Health must not be cached")
        print("PASS health", flush=True)

        for input_format, dataset, org_id, org_name in [
            ("csv", "iCarol", "87138316", "Woda Cooper Companies - Cumberland Meadows"),
            ("json", "json_test", "1", "Test Organization"),
        ]:
            paths = sorted((DATA / dataset).glob(f"*.{input_format}"))
            require(bool(paths), f"Missing fixture {dataset}")
            upload = io.BytesIO()
            with zipfile.ZipFile(upload, "w") as archive:
                for path in paths:
                    archive.writestr(path.name, path.read_bytes())
            response = client.post(
                "transform", data={"input_format": input_format},
                files={"zip_file": ("input.zip", upload.getvalue(), "application/zip")},
            )
            check_archive(response, org_id, org_name)
            print(f"PASS {input_format} ZIP content", flush=True)

        response = client.post("transform/stream", files=[
            ("files", (path.name, path.read_bytes(), "application/json"))
            for path in sorted((DATA / "json_test").glob("*.json"))
        ])
        check_archive(response, "1", "Test Organization")
        print("PASS JSON multipart content", flush=True)

        response = client.post("transform", files={
            "zip_file": ("invalid.zip", b"not a zip", "application/zip"),
        })
        require(response.status_code == 422, f"Invalid ZIP returned {response.status_code}")
        require(response.json()["detail"] == "Invalid zip file", "Unexpected validation error")
        require("content-disposition" not in response.headers, "Error returned a download")
        print("PASS invalid ZIP rejection", flush=True)
        response = client.get("health")
        require(response.status_code == 200 and response.json()["status"] == "ok", "Recovery health failed")
        print("PASS health after rejection", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Explicit approved API URL, including any path prefix")
    args = parser.parse_args()
    print(f"Started {datetime.now(timezone.utc).isoformat()}", flush=True)
    run(args.base_url)
    print("PASS smoke only; image identity, runtime permissions and rollback require separate evidence")


if __name__ == "__main__":
    main()
