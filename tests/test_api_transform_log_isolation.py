import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import importlib

import httpx
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.lib.transform.logger import TransformerLog, transformer_log

api = importlib.import_module("src.api.app")


# Uppercase and hyphen never occur in tempfile's random names or pytest's
# tmp_path, so these markers can only reach the log via the uploaded filenames.
ALPHA = "REQ-ALPHA"
BETA = "REQ-BETA"

@pytest.fixture
def logs(monkeypatch):
    captured = []

    class ObservedLog(TransformerLog):
        def clear(self):
            captured.append((self, list(self.entries)))
            super().clear()

    monkeypatch.setattr(api, "TransformerLog", ObservedLog)
    return captured

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



@pytest.mark.parametrize("post", [_post_transform, _post_transform_stream])
def test_sequential_requests_do_not_share_transformer_log(client, post, logs, tmp_path):
    before = list(transformer_log.entries)
    for tag in (ALPHA, BETA):
        response = post(client, tag)
        assert response.status_code == 201, response.text
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            records = [json.loads(archive.read(name)) for name in archive.namelist()]
        assert records == [{"id": f"{tag}-1", "name": f"{tag} org"}]
        assert list(tmp_path.iterdir()) == []
    assert len(logs) == 2
    assert logs[0][0] is not logs[1][0]
    assert any(ALPHA in line for line in logs[0][1])
    assert any(BETA in line for line in logs[1][1])
    assert all(ALPHA not in line for line in logs[1][1])
    assert all(not log.entries for log, _ in logs)
    assert transformer_log.entries == before


@pytest.mark.parametrize("post", [_post_transform, _post_transform_stream])
def test_concurrent_requests_are_isolated(client, post, logs, monkeypatch, tmp_path):
    barrier = Barrier(2)
    original = api.searching_and_assigning

    def interleave(results, *, log):
        barrier.wait(timeout=10)
        return original(results, log=log)

    monkeypatch.setattr(api, "searching_and_assigning", interleave)
    def run(tag):
        with TestClient(app) as concurrent_client:
            return post(concurrent_client, tag)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(run, [ALPHA, BETA]))
    assert [r.status_code for r in responses] == [201, 201]
    assert len(logs) == 2
    for log, entries in logs:
        assert not log.entries
        assert any(ALPHA in line for line in entries) != any(BETA in line for line in entries)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("post", [_post_transform, _post_transform_stream])
@pytest.mark.parametrize("failure", ["validation", "malformed", "transform", "write", "archive"])
def test_failure_cleanup_and_recovery(client, post, logs, monkeypatch, tmp_path, failure):
    with monkeypatch.context() as patch:
        def fail(*args, **kwargs):
            raise OSError("synthetic failure")

        if failure == "transform":
            patch.setattr(api, "searching_and_assigning", fail)
        elif failure == "write":
            patch.setattr(api, "save_objects_to_json", fail)
        elif failure == "archive":
            patch.setattr(zipfile.ZipFile, "write", fail)
        elif failure == "validation":
            def reject(*args, **kwargs):
                kwargs["log"].log("FAILED-RUN")
                raise ValueError("synthetic invalid mapping")
            patch.setattr(api, "build_collections", reject)
            patch.setattr(api, "build_collections_from_json", reject)
        if failure == "malformed":
            if post is _post_transform:
                response = client.post("/transform", files={"zip_file": ("bad.zip", b"invalid")})
            else:
                response = client.post("/transform/stream", files=[
                    ("files", ("bad_organization_mapping.json", JSON_MAPPING)),
                    ("files", ("bad.json", b"invalid")),
                ])
        else:
            with TestClient(app, raise_server_exceptions=False) as failing_client:
                response = post(failing_client, "FAILED-RUN")
        assert response.status_code == (422 if failure in ("validation", "malformed") else 500)
    assert list(tmp_path.iterdir()) == []
    assert all(not log.entries for log, _ in logs)
    assert client.get("/health").status_code == 200
    assert post(client, BETA).status_code == 201
    assert all("FAILED-RUN" not in line for line in logs[-1][1])
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("post", [_post_transform, _post_transform_stream])
@pytest.mark.parametrize("interrupt", ["start", "body", "cancel"])
def test_interrupted_response_cleanup_and_recovery(client, post, logs, monkeypatch, tmp_path, interrupt):
    # Exercise the actual ASGI app. TestClient buffers downloads, so closing a
    # TestClient response alone would not simulate a disconnected consumer.
    class CaptureRequest:
        def post(self, path, **kwargs):
            return httpx.Request("POST", "http://testserver" + path, **kwargs)

    request = post(CaptureRequest(), ALPHA)
    body = request.read()

    async def run():
        delivered = False
        scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
                 "method": "POST", "path": request.url.path, "raw_path": request.url.raw_path,
                 "query_string": b"", "headers": request.headers.raw,
                 "scheme": "http", "server": ("testserver", 80), "client": ("local", 1),
                 "http_version": "1.1"}

        async def receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.Event().wait()

        async def send(message):
            if message["type"] == ("http.response.start" if interrupt == "start" else "http.response.body"):
                if interrupt == "cancel":
                    raise asyncio.CancelledError()
                raise OSError("synthetic disconnected consumer")

        try:
            await app(scope, receive, send)
        except (OSError, asyncio.CancelledError):
            pass
    asyncio.run(run())
    assert logs and all(not log.entries for log, _ in logs)
    assert list(tmp_path.iterdir()) == []
    assert client.get("/health").status_code == 200
    assert post(client, BETA).status_code == 201
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("post", [_post_transform, _post_transform_stream])
def test_lifecycle_diagnostics_share_response_request_id(client, post, caplog):
    response = post(client, ALPHA)
    lifecycle = [record.message for record in caplog.records if "Transformation lifecycle" in record.message]
    assert len(lifecycle) == 1
    assert response.headers["X-API-REQUEST-ID"] in lifecycle[0]
    assert "outcome=completed" in lifecycle[0]
    assert ALPHA not in lifecycle[0]


@pytest.mark.parametrize("endpoint", ["/transform", "/transform/stream"])
def test_early_validation_cleanup(client, endpoint, logs, tmp_path):
    field = "zip_file" if endpoint == "/transform" else "files"
    response = client.post(endpoint, files={field: ("invalid.txt", b"invalid")})
    assert response.status_code == 422
    assert logs and all(not log.entries for log, _ in logs)
    assert list(tmp_path.iterdir()) == []
    assert client.get("/health").status_code == 200
    post = _post_transform if endpoint == "/transform" else _post_transform_stream
    assert post(client, BETA).status_code == 201
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("spec_version", ["2.0", "2.4"])
def test_cancellation_waits_for_inflight_archive_read(monkeypatch, tmp_path, spec_version):
    from threading import Event

    entered = Event()
    release = Event()
    closed = Event()
    path = tmp_path / "output.zip"
    path.write_bytes(b"synthetic archive")

    def blocked_iterator(path):
        try:
            with path.open("rb") as stream:
                entered.set()
                assert release.wait(timeout=5)
                yield stream.read()
        finally:
            closed.set()
            path.unlink(missing_ok=True)

    monkeypatch.setattr(api, "_iter_and_cleanup", blocked_iterator)

    async def run():
        response = api.CleanupStreamingResponse(path)

        async def receive():
            await asyncio.Event().wait()

        async def send(message):
            pass

        task = asyncio.create_task(response(
            {"type": "http", "asgi": {"spec_version": spec_version}}, receive, send
        ))
        try:
            async with asyncio.timeout(5):
                while not entered.is_set():
                    await asyncio.sleep(0.001)
            task.cancel()
            await asyncio.sleep(0.01)
            assert not task.done(), "response must wait for its active file read"
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert closed.is_set()
    assert not path.exists()
