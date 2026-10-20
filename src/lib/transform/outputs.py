import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OutputSummary:
    """Artifact counts for a successfully verified and published run."""

    expected: int
    written: int
    verified: int


def _check_destination(destination):
    """Accept only a missing destination or a real, empty directory."""
    if destination.is_symlink() or destination.is_junction():
        raise ValueError(
            f"Output directory '{destination}' is a link. Choose a new or empty directory."
        )
    if destination.exists():
        if not destination.is_dir():
            raise ValueError(
                f"Output destination '{destination}' is not a directory. "
                "Choose a new or empty directory."
            )
        if any(destination.iterdir()):
            raise ValueError(
                f"Output directory '{destination}' is not empty. "
                "No files were changed. Choose a new or empty directory "
                "(CLI: --output-dir PATH)."
            )


def _verify_outputs(staging, filenames):
    """Read back exactly the planned JSON artifacts; failures are I/O errors."""
    if {path.name for path in staging.iterdir()} != set(filenames):
        raise OSError("Staged output filenames/count do not match the planned artifacts.")
    for filename in filenames:
        try:
            with (staging / filename).open(encoding="utf-8") as stream:
                json.load(stream)
        except (ValueError, UnicodeError) as exc:
            raise OSError(f"Could not verify staged JSON artifact {filename!r}.") from exc
    return len(filenames)


def save_objects_to_json(objects_data, output_dir):
    """Preflight, stage and verify all JSON before publishing the directory.

    Refuse nonempty destinations. A sibling lock excludes other cooperating
    writers; staging is on the same filesystem for directory rename publication.
    Handled failures clean staging. This is not a crash-durability guarantee.
    """
    # Resolve parents for a stable lock name, but never follow a destination link.
    requested = Path(os.path.abspath(output_dir))
    destination = requested.parent.resolve() / requested.name
    planned_outputs = []
    seen_targets = {}
    for group_index, (object_type, objects_list) in enumerate(objects_data, start=1):
        for record_index, obj_dict in enumerate(objects_list, start=1):
            context = (
                f"{object_type!r} group {group_index}, record {record_index}"
            )
            obj_id = obj_dict.get("id")
            if not obj_id or (isinstance(obj_id, str) and not obj_id.strip()):
                raise ValueError(f"Missing nonempty output ID for {context}.")

            filename = f"{object_type}_{obj_id}.json"
            if any(char in filename for char in '/\\<>:"|?*') or any(
                ord(char) < 32 for char in filename
            ):
                raise ValueError(
                    f"Unsafe output filename {filename!r} for {context}. "
                    "Object types and IDs must form a single portable filename."
                )
            target = os.path.normcase(filename)
            if target in seen_targets:
                raise ValueError(
                    f"Duplicate output target {filename!r} for {context} "
                    f"(ID {obj_id!r}); first seen at {seen_targets[target]}."
                )
            seen_targets[target] = context
            planned_outputs.append((filename, obj_dict))

    _check_destination(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    lock = destination.with_name(f".{destination.name}.hsds-lock")
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(
            f"Output directory '{destination}' is reserved by another run "
            f"(lock: '{lock}'). Choose another directory or wait for that run to finish. "
            "If a run crashed, remove its lock only after confirming it has stopped."
        ) from exc
    os.close(lock_fd)
    try:
        _check_destination(destination)
        with tempfile.TemporaryDirectory(
            prefix=f".{destination.name}.hsds-stage-", dir=destination.parent
        ) as staging_dir:
            staging = Path(staging_dir)
            written = 0
            for filename, obj_dict in planned_outputs:
                try:
                    stream = (staging / filename).open("x", encoding="utf-8")
                except FileExistsError as exc:
                    raise ValueError(
                        f"Duplicate output target {filename!r} on this filesystem."
                    ) from exc
                with stream:
                    try:
                        json.dump(
                            obj_dict, stream, indent=2, ensure_ascii=False, allow_nan=False
                        )
                    except (TypeError, ValueError) as exc:
                        raise ValueError(
                            f"Could not serialize output {filename!r} as JSON: {exc}"
                        ) from exc
                written += 1
            verified = _verify_outputs(staging, [name for name, _ in planned_outputs])
            summary = OutputSummary(len(planned_outputs), written, verified)
            _check_destination(destination)
            # Removing only an empty directory accommodates the API's temp dir
            # and Windows, where rename cannot replace an existing directory.
            existed = destination.exists()
            if existed:
                destination.rmdir()
            try:
                staging.rename(destination)
            except OSError:
                if existed:
                    try:
                        destination.mkdir()
                    except FileExistsError:
                        # A concurrent external writer owns whatever appeared.
                        pass
                raise
        logging.getLogger("hsds.outputs").info(
            "Output published: expected=%d written=%d verified=%d",
            summary.expected, summary.written, summary.verified,
        )
        return summary
    finally:
        lock.unlink()
