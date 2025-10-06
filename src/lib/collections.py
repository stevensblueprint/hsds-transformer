from pathlib import Path
import re
from parser import parse_input_csv, parse_nested_mapping
from mapper import nested_map

def build_collections(data_directory: str):
    data_directory = Path(data_directory)
    results = []

    for mapping_file in data_directory.glob("*_mapping.csv"):
        match = re.match(r"(.+)_([A-Za-z0-9]+)_mapping\.csv", mapping_file.name)
        if not match:
            continue

        input_base, object_type = match.groups()
        input_file = data_directory / f"{input_base}.csv"

        if not input_file.exists():
            continue

        input_rows = parse_input_csv(str(input_file), input_base)
        mapping = parse_nested_mapping(str(mapping_file), input_base)

        objects = []
        for row in input_rows:
            mapped = nested_map(row, mapping)

            if isinstance(mapped, dict) and object_type in mapped:
                mapped = mapped[object_type]
            objects.append(mapped)

        results.append((object_type), objects)

    return results