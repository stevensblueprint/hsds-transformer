import zipfile
from pathlib import Path

from fastapi import HTTPException


# helper function to check for duplicate filenames (even in subdirectories)
def validate_no_duplicate_filenames(zf: zipfile.ZipFile) -> None:
    seen_filenames = set()

    for file_info in zf.infolist():
        if file_info.is_dir():
            continue

        filename = Path(file_info.filename).name

        if filename in seen_filenames:
            raise HTTPException(
                status_code=422,
                detail=f"Duplicate filename found in zip: {filename}",
            )

        seen_filenames.add(filename)

# helper function to ensure json uploads contain required files
def validate_json_transform_files(input_dir: str) -> None:
    files = [p for p in Path(input_dir).rglob("*") if p.is_file()]

    has_json_file = False
    has_mapping_file = False

    for file_path in files:
        if file_path.suffix.lower() == ".json":
            has_json_file = True

        if file_path.name.lower().endswith("_mapping.csv"):
            has_mapping_file = True

    if not has_json_file:
        raise HTTPException(status_code=422, detail="JSON input file is missing")

    if not has_mapping_file:
        raise HTTPException(status_code=422, detail="Mapping file is missing")