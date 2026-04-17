# Issue #122 Implementation Plan - `POST /transform/stream`

## Goal
Add a new `POST /transform/stream` endpoint that accepts multipart uploads of source JSON and JSON mapping files, stages them in a request-scoped temp workspace, enforces upload/file safety constraints, runs the existing transformation pipeline, and always cleans up temporary files.

## Scope and Constraints
- Keep existing `POST /transform` unchanged.
- New endpoint: `POST /transform/stream`.
- Input: `multipart/form-data` with repeated `files` parts.
- Accept only `.json` files.
- Classify mappings as files ending in `*_mapping.json`; all other `.json` files are source data.
- Enforce request-size limits and reject:
  - unsafe filenames
  - duplicate filenames
  - missing source JSON files
  - missing mapping JSON files
- On success: return transformed output as `.zip`.
- Cleanup temp workspace on:
  - success
  - validation error
  - transform error
  - client disconnect / cancellation

## Current Code Touchpoints
- `src/api/app.py`
  - Add new route for `/transform/stream`.
  - Reuse existing transform pipeline flow where possible.
- `src/api/utils.py`
  - Add multipart staging + validation helpers.
- Transformer pipeline reuse:
  - `build_collections(...)`
  - `searching_and_assigning(...)`
  - `save_objects_to_json(...)`

## Implementation Phases

### Phase 1 - Request Staging and Safety Helpers
Add helper functions in `src/api/utils.py`:

1. `sanitize_upload_filename(name: str) -> str`
   - Allow basename only; reject path traversal and separators (`/`, `\`, `..`).
   - Reject empty/hidden/invalid filenames.
   - Require `.json` extension.

2. `stage_multipart_uploads(files: list[UploadFile], input_dir: Path, max_upload_bytes: int) -> StagingSummary`
   - Stream each upload to disk in chunks.
   - Track cumulative bytes across all files.
   - Abort with `413` if limit exceeded.
   - Detect duplicate filenames.
   - Return counts/metadata:
     - total files
     - source file count
     - mapping file count
     - total bytes staged

3. `validate_staged_workspace(summary: StagingSummary) -> None`
   - Require at least one source JSON.
   - Require at least one `*_mapping.json`.
   - Raise `422` with specific error details.

4. `create_output_zip(output_dir: Path, zip_path: Path) -> None`
   - File-backed zip generation from transformed JSON files.

### Phase 2 - New `/transform/stream` Route
Implement in `src/api/app.py`:

1. Define endpoint:
   - `@app.post("/transform/stream", status_code=201, response_class=StreamingResponse or FileResponse)`

2. Request handling flow:
   - Create request-scoped temp workspace:
     - `input/`
     - `output/`
   - Stage multipart files using helper.
   - Validate staged files.
   - Add a placeholder code comment where JSON transform pipeline calls will go (do not wire transform logic in this issue yet).
   - Placeholder should mark future call site for:
      - `build_collections(input_dir)`
      - `searching_and_assigning(results)`
      - `save_objects_to_json(results, output_dir)`
   - Package output zip and return response using existing API response pattern.
   - Return zip response with:
     - `Content-Type: application/zip`
     - `Content-Disposition: attachment; filename=transformed.zip`
   - Keep middleware behavior unchanged in this issue; middleware-safe streaming is handled by issue `#120`.

3. Error mapping:
   - `413` for upload size violations.
   - `422` for invalid uploads/mapping validation errors.
   - `500` only for unexpected internal failures.

4. Cleanup:
   - Ensure temp workspace is deleted in all paths via context manager / `try/finally`.
   - Do not leave residual files if client disconnects during processing.

### Phase 3 - Validation Scenarios and Manual Verification
Validate behavior with manual API tests:

1. Happy path
   - Multipart with valid source JSON + `*_mapping.json`
   - Expect `201` and valid transformed zip.

2. Missing mappings
   - No `*_mapping.json`
   - Expect `422`.

3. Duplicate filenames
   - Same filename uploaded twice
   - Expect `422`.

4. Unsafe filenames
   - Filenames containing path traversal / separators
   - Expect `4xx` (`422` preferred).

5. Oversized request
   - Exceed configured max bytes
   - Expect `413`.

6. Mapping/path validation failure
   - If issue `#121` is merged, invalid mapping paths should return `422`.
   - If issue `#121` is not merged yet, treat this behavior as out of scope for `#122`.

## Sub-Issue Ownership Boundaries
- `#122` owns endpoint wiring, multipart staging, upload safety checks, workspace lifecycle, and passing `input_dir` into the collection build path.
- `#117` owns streamed JSON collection build internals.
- `#121` owns JSON mapping-path validation behavior.
- `#118` owns streamed/file-backed ZIP response mechanics.
- `#120` owns middleware-safe handling for streaming and binary responses.
- `#119` owns automated tests for the streamed JSON transform flow.

## Proposed Constants / Config
- `MAX_MULTIPART_UPLOAD_BYTES` (default value to be defined; e.g., 50MB or team-approved value).
- Chunk size for upload writes (e.g., 1MB).

## Deliverables
1. New `POST /transform/stream` endpoint.
2. Multipart staging + validation helpers in `src/api/utils.py`.
3. Error handling aligned to acceptance criteria.
4. Basic usage notes (README/API doc snippet if desired).

## Acceptance Criteria Mapping
- New route exists and `/transform` unchanged -> **Phase 2**
- Multipart repeated `files` supported -> **Phase 1 + 2**
- Request-scoped temp staging -> **Phase 2**
- Unsafe/duplicate filenames rejected -> **Phase 1**
- Request size limits enforced -> **Phase 1**
- Temp files always cleaned -> **Phase 2**
- No residual files on disconnect/failure -> **Phase 2**
- Pass staged input dir into collection builder -> **Phase 2**

## Out of Scope (for this issue)
- Replacing existing CSV transformer internals.
- Incremental/record-by-record transform while upload is in progress.
- New auth/rate-limit policy changes.
