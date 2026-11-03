# Request-owned transformation state (BLU-10)

Each API transformation receives its own `TransformerLog` through an async
FastAPI yield dependency. CSV/JSON collection building and linking receive that
log explicitly. The dependency clears its entries in `finally`, including on
validation errors, pipeline errors and cancellation. It stays alive through
response consumption. The process-wide logger remains only the backwards
compatible default for library and CLI callers; API requests neither append to
nor clear it. API calls preserve supplied IDs and do not reset the CLI's legacy
ID-generation counter. Concurrent CLI ID generation is outside this change.

The existing middleware assigns the request ID to `request.state`; lifecycle
summaries use the same ID as `X-API-REQUEST-ID`. Summaries contain route, outcome
(exception class or completed), and entry count, not dataset contents or full
transformation logs. A completed lifecycle does not prove the client received
all bytes: a disconnect can be handled by the streaming stack.

The download response owns its archive and closes the iterator and unlinks the
file in `finally`, even when sending response headers fails before iteration.
The asyncio streaming wrapper shields and joins each threadpool read before
closing its generator, including cancellation while a read is in flight. This
uses the asyncio backend used by the configured Uvicorn server.
The iterator's own `finally` remains. Input/output temporary directories and the
multipart workspace `finally` remain request-local. Abrupt process termination
and filesystem cleanup failures are not claimed to be recoverable.

## Verification

Base: `8cccd0b53e0d1b05e7483d7041816f033fcbebd5` (current main fetched October 27).
The original PR159 strict-xfail diagnostics were run with `--runxfail` before
editing production code: **2 failed**, with earlier request markers retained
by both endpoints. The updated tests remove the xfail and observe request-owned
logs at disposal, preserving assertions on actual output content.

`tests/test_api_transform_log_isolation.py` covers both endpoints:

- sequential success, exact synthetic organization JSON and empty temp roots;
- overlapping threaded requests synchronized between building and linking;
- validation rejection before and after staging/building;
- malformed ZIP or malformed JSON (the stream route does not accept archives);
- injected linking, JSON-write and archive-write failures;
- actual ASGI send errors before response iteration and during body sending,
  plus task cancellation during body sending and controlled in-flight reads
  under ASGI 2.0 and 2.4;
- released log entries, no leftover workspaces/archives, then health and
  successful transformation recovery;
- lifecycle diagnostics correlated to response IDs without source markers.

Tests use tiny synthetic fixtures and temporary directories. TestClient buffers
responses; interruption tests therefore drive the ASGI app directly with failed
send callbacks rather than pretending a closed buffered response is a network
disconnect. They do not emulate kernel socket timing or process termination.

Follow-up review of `543bf84bdacda3a9a3a940575eb4dc1a8eb83282` found that
those six ASGI interruption cases supplied mixed-case HTTPX header names. That
could bypass the multipart transformation path, so their earlier passing result
did not establish interrupted-download coverage. The corrected harness lowercases
ASGI header names and requires a 201 response, an archive containing the exact
ALPHA organization, a nonempty chunk for body interruption, and execution of the
failure injection. It also checks ALPHA diagnostics before successful BETA
recovery. With these assertions added first, all six cases failed on the original
headers; after header correction all six passed. This was a test coverage defect;
no production cleanup regression was reproduced.

Use the pinned uv from README with a writable cache:

```sh
uv run --locked --extra api python -m pytest tests/test_api_transform_log_isolation.py -q
uv run --locked --extra api python -m pytest tests/ -q
uv run --locked --extra api ruff check .
uv build
```

## Integration boundaries

The HTTP 201 ZIP success contract and transformed contents are unchanged.
PR158 owns bounded ZIP extraction; this change leaves extraction policy alone.
PR160 owns shared writer/CLI/API integration; preserve explicit `log=log` calls,
request dependency lifetime, and archive ownership when combining those changes.
PR154 corpus inventory is untouched. No BLU-24 semantic/provenance redesign or
HSDS version migration is included.
