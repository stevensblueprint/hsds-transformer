import os
import json


def ingest_json_directory(directory_path: str) -> list[dict]:
    """
    Read all .json files in the given directory and return their parsed contents.
    
    Parameters:
        directory_path (str): Path to the directory containing JSON files.
    
    Returns:
        list[dict]: A list of dictionaries parsed from each JSON file found in the directory.
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
    Retrieve all values located at the given dot-separated path within an HSDS directory, supporting list segments denoted with [] (e.g., "locations[].phones[].number").
    
    Parameters:
        hsds_directory (dict): HSDS directory represented in canonical Python dict form.
        path (str): Dot-separated path string. Append "[]" to a segment name to indicate the segment is expected to be a list and should be flattened across branches.
    
    Returns:
        tuple: A tuple containing every value found at the specified path across all branches.
    
    Raises:
        ValueError: If a path segment is missing in every applicable branch such that the path cannot be fully traversed.
        ValueError: If a path segment marked with "[]" is not a list in the input data.
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