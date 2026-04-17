from __future__ import annotations

import csv
from typing import Iterable

from .generator import FieldSpec


HEADER = [
    "path",
    "input_files_field",
    "split",
    "strip",
    "description",
    "required",
]


def write_mapping_template_csv(rows: Iterable[FieldSpec], out_file: str) -> None:
    """Write the flattened rows to *out_file* as a mapping template CSV."""

    with open(out_file, "x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerow([""] * len(HEADER))

        for row in rows:
            required = "true" if row.required else "false"
            writer.writerow([row.path, "", "", "", row.description, required])
