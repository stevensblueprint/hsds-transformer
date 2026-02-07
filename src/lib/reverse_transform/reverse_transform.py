import os
import json


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
        HSDS_directory: Python dictionary in canonical HSDS format.

    Returns:
        All items at path. If multiple branches can be traversed to get to 
        the same path, one item is pulled from each branch.

    Raises:
        ValueError: If, following every actual path described by input path,
            the path cannot be traversed fully. E.g. for path
            locations[].phones[].number, if there are zero locations, or if any
            location has zero phones, or if any phone does not have a number,
            this error with be thrown.
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
            try:
                for t in temp:
                    assert isinstance(t, list)
                    temp2 += t
            except AssertionError:
                raise ValueError(f"Poorly formatted input. Expected all {p} in "
                    f"{path_string} to be in a list, but found one in a non-list "
                    f"in {curr} \n---") from None
            temp = temp2
        curr = temp

    return tuple(curr)
