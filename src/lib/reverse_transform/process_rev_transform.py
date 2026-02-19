from .buildcsv import reverseTransform
from .parser import parse_input_csv
from .reverse_transform import ingest_json_directory, get_path_value
from pathlib import Path
from dataclasses import dataclass

@dataclass
class CsvMapping:
    name: str
    source_file: Path
    fields: list[tuple[str,str]]

def process_mappings(mapping_dir: Path):
    mappingData = []

    for file in mapping_dir.glob("*.csv"):

        mappingTuple = parse_input_csv(file)

        fileName = file.name.split("_")[0]

        mappingData.append(
            CsvMapping(
                name=fileName,
                source_file = file,
                fields = mappingTuple,
            )
        )
    return mappingData


