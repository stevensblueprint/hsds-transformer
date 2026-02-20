import os
import re
import json
from pathlib import Path
from dataclasses import dataclass
from .parser import parse_input_csv


def ingest_json_directory(directory_path: str) -> list[dict]:
    """
    Read all JSON files from a directory and return as a list of dictionaries.

    Args:
        directory_path: Path to directory containing JSON files

    Returns:
        List of dictionaries, one per JSON file
    """
    results = []

    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                results.append(json.load(f))

    return results


def get_path_value(hsds_directory: dict, path: str) -> tuple:
    """
    Gets all items at a given path in an HSDS directory. If multiple items
    lie at the same path in different branches, returns all of them.

    Args:
        hsds_directory: Python dictionary in canonical HSDS format.
        path:           Path a la mapping template, e.g. 'id', 'program.name',
                        'contacts[].email'.

    Returns:
        All items at path. If multiple branches can be traversed to get to
        the same path, one item is pulled from each branch.

    Raises:
        ValueError: If, following every actual path described by input path,
            the path cannot be traversed fully. E.g. for path
            locations[].phones[].number, if there are zero locations, or if any
            location has zero phones, or if any phone does not have a number,
            this error will be thrown.
        ValueError: If, at a path node specifying a list, e.g. locations[],
            there is not a list, but a singular object, this error will be
            thrown.
    """
    path_string = path

    path = path.split('.')

    curr = []
    curr.append(hsds_directory)
    for p in path:
        p_is_list = False
        temp = []
        if p[-2:] == "[]":
            p = p[:-2]
            p_is_list = True
        for c in curr:
            try:
                temp.append(c[p])
            except KeyError as ke:
                raise ValueError(f"Could not find path \"{p}\" in item {c}.") from ke
        if p_is_list:
            temp2 = []
            for t in temp:
                if not isinstance(t, list):
                    raise ValueError(f"Poorly formatted input. Expected all {p} in "
                        f"{path_string} to be in a list, but found one in a non-list "
                        f"in {curr} \n---") from None
                temp2 += t
            temp = temp2
        curr = temp

    return tuple(curr)


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


def get_entity_objects(spec: CsvMapping, all_objects: list[dict], hsds_path: Path) -> list[dict] | None:
    """
    Returns the list of dicts relevant to this mapping's entity type, drawn from all_objects.
    Returns None if the mapping filename doesn't match the expected format.
    """
    match = re.match(r".+_([A-Za-z0-9]+)_mapping\.csv", spec.source_file.name)
    if not match:
        return None

    entity_type = match.group(1)

    entity_ids = {
        f.stem.split('_', 1)[1]
        for f in hsds_path.glob(f"{entity_type}_*.json")
    }

    if entity_ids:
        return [d for d in all_objects if d.get('id') in entity_ids]

    if entity_type.endswith(("s", "sh", "ch", "x", "z")):
        nested_key = entity_type + "es"
    else:
        nested_key = entity_type + "s"

    dict_list = []
    for parent in all_objects:
        dict_list.extend(parent.get(nested_key, []))
    return dict_list
