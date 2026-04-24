from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from fastapi import UploadFile


UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024


class UploadValidationError(ValueError):
    pass


class UploadSizeLimitError(ValueError):
    pass


@dataclass(frozen=True)
class StagingSummary:
    total_files: int
    source_file_count: int
    mapping_file_count: int
    total_bytes: int


class AsyncIteratorWrapper:
    """The following is a utility class that transforms a
    regular iterable to an asynchronous one.

    link: https://www.python.org/dev/peps/pep-0492/#example-2
    """

    def __init__(self, obj):
        self._it = iter(obj)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            value = next(self._it)
        except StopIteration:
            raise StopAsyncIteration
        return value


def sanitize_upload_filename(name: str) -> str:
    filename = (name or "").strip()
    if not filename:
        raise UploadValidationError("Uploaded file is missing a filename")
    if "\x00" in filename:
        raise UploadValidationError("Filename contains invalid null bytes")

    path = Path(filename)
    if path.name != filename:
        raise UploadValidationError(f"Unsafe filename '{filename}'")
    if filename in {".", ".."} or filename.startswith("."):
        raise UploadValidationError(f"Unsafe filename '{filename}'")
    if "/" in filename or "\\" in filename or ".." in filename:
        raise UploadValidationError(f"Unsafe filename '{filename}'")
    if not filename.lower().endswith(".json"):
        raise UploadValidationError(f"Only .json files are allowed: '{filename}'")

    return filename


def _is_mapping_filename(filename: str) -> bool:
    return filename.lower().endswith("_mapping.json")


async def stage_multipart_uploads(
    files: Sequence[UploadFile],
    input_dir: Path,
    max_upload_bytes: int,
    *,
    chunk_size: int = UPLOAD_CHUNK_SIZE_BYTES,
) -> StagingSummary:
    if max_upload_bytes <= 0:
        raise ValueError("max_upload_bytes must be greater than zero")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    input_dir.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    total_files = 0
    source_file_count = 0
    mapping_file_count = 0
    seen_filenames: set[str] = set()

    for upload in files:
        safe_name = sanitize_upload_filename(upload.filename or "")
        if safe_name in seen_filenames:
            raise UploadValidationError(f"Duplicate filename: '{safe_name}'")
        seen_filenames.add(safe_name)

        output_path = input_dir / safe_name
        with output_path.open("wb") as destination:
            while True:
                chunk = await upload.read(chunk_size)
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > max_upload_bytes:
                    raise UploadSizeLimitError(
                        f"Upload size exceeds limit of {max_upload_bytes} bytes"
                    )

                destination.write(chunk)

        await upload.close()
        total_files += 1
        if _is_mapping_filename(safe_name):
            mapping_file_count += 1
        else:
            source_file_count += 1

    return StagingSummary(
        total_files=total_files,
        source_file_count=source_file_count,
        mapping_file_count=mapping_file_count,
        total_bytes=total_bytes,
    )


def validate_staged_workspace(summary: StagingSummary) -> None:
    if summary.total_files == 0:
        raise UploadValidationError("At least one uploaded file is required")
    if summary.source_file_count == 0:
        raise UploadValidationError("At least one source JSON file is required")
    if summary.mapping_file_count == 0:
        raise UploadValidationError(
            "At least one mapping file ending in *_mapping.json is required"
        )
