"""Bounded extraction into a fresh, request-owned temporary directory."""

import stat
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from fastapi import HTTPException


@dataclass(frozen=True)
class ZipLimits:
    # Provisional budgets: 10x the compressed upload cap in total, with a
    # smaller per-file cap and finite inode/expansion work per request.
    max_members: int = 1000
    max_file_bytes: int = 20 * 1024 * 1024
    max_total_bytes: int = 50 * 1024 * 1024
    max_ratio: int = 100


def _budget(condition: bool, detail: str) -> None:
    if condition:
        raise HTTPException(413, f"Zip {detail} limit exceeded; split the upload")


def _relative_path(info: zipfile.ZipInfo) -> Path:
    name = info.filename
    parts = PurePosixPath(name).parts
    if (
        not parts or "\x00" in info.orig_filename or "\\" in name
        or PurePosixPath(name).is_absolute() or PureWindowsPath(name).drive
        or ".." in parts
    ):
        raise HTTPException(422, "Zip member path must stay within the upload folder")
    mode = stat.S_IFMT(info.external_attr >> 16)
    if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise HTTPException(422, "Zip entries must be regular files or directories")
    if info.flag_bits & 1:
        raise HTTPException(422, "Encrypted zip entries are not supported; upload an unencrypted zip")
    if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        raise HTTPException(422, "Unsupported zip compression; use stored or deflated entries")
    if info.is_dir() and info.file_size:
        raise HTTPException(422, "Zip directory entries must be empty")
    return Path(*parts)


def validate_zip_budget(archive: zipfile.ZipFile, limits: ZipLimits) -> None:
    members = archive.infolist()
    _budget(len(members) > limits.max_members, "members")
    total = 0
    for info in members:
        _relative_path(info)
        _budget(info.file_size > limits.max_file_bytes, "expanded file bytes")
        total += info.file_size
        _budget(total > limits.max_total_bytes, "total expanded bytes")
        _budget(info.file_size > limits.max_ratio * info.compress_size, "compression ratio")


def extract_zip(archive: zipfile.ZipFile, destination: Path, limits: ZipLimits) -> None:
    """Reject before writing past a budget; caller owns workspace cleanup.

    Only stored/deflated streams are accepted to keep decompression behavior
    predictable. The private workspace must be fresh and inaccessible to writers.
    """
    validate_zip_budget(archive, limits)
    root = destination.resolve()
    total = 0
    try:
        for count, info in enumerate(archive.infolist(), 1):
            _budget(count > limits.max_members, "members")
            target = (root / _relative_path(info)).resolve()
            if not target.is_relative_to(root):
                raise HTTPException(422, "Zip member path must stay within the upload folder")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            # Exclusive creation also rejects normalized-name collisions.
            with archive.open(info) as source, target.open("xb") as output:
                while True:
                    remaining = min(
                        limits.max_file_bytes - written,
                        limits.max_total_bytes - total,
                        limits.max_ratio * info.compress_size - written,
                    )
                    chunk = source.read(min(64 * 1024, remaining + 1))
                    if not chunk:
                        break
                    written += len(chunk)
                    total += len(chunk)
                    _budget(written > limits.max_file_bytes, "expanded file bytes")
                    _budget(total > limits.max_total_bytes, "total expanded bytes")
                    _budget(written > limits.max_ratio * info.compress_size, "compression ratio")
                    output.write(chunk)
                if written != info.file_size:
                    raise HTTPException(422, "Zip entry size mismatch; recreate the zip")
    except (zipfile.BadZipFile, EOFError, zlib.error, NotImplementedError, RuntimeError) as exc:
        raise HTTPException(422, "Invalid or unsupported zip entry; recreate the zip") from exc
    except (FileExistsError, IsADirectoryError, NotADirectoryError) as exc:
        raise HTTPException(422, "Conflicting zip member paths; rename entries") from exc
