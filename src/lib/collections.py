from pathlib import Path
import re
from .parser import parse_input_csv, parse_nested_mapping
from .mapper import nested_map

def build_collections(data_directory: str):
    """
    From multiple mapping and input CSV files, returns a list of tuples like: [("organization", [dicts]), ("location", [dicts]), ...]
    Each mapping file name MUST follow this format: "<input_file_name>_<object_type>_mapping.csv
    This function pairs each input CSV with its correspodning mapping file and converts flat CSV rows into nested dictionaries
    """
    
    data_directory = Path(data_directory) # Converts provided folder path into a Path object
    results = [] # List of tuples like ("organization", [dict_list])

    # Goes through every CSV file in the folder that ends with "_mapping.csv"
    for mapping_file in data_directory.glob("*_mapping.csv"):
        match = re.match(r"(.+)_([A-Za-z0-9]+)_mapping\.csv", mapping_file.name) # Parses and extracts name before "_mapping" using regex
        
        # Skips files with no _mapping ending
        if not match:
            continue

        input_name, object_type = match.groups() # Grabs the name and type of object for labeling in results
        input_file = data_directory / f"{input_name}.csv" # Uses the extracted name to find the corresponding input CSV file

        # Skips this mapping if the matching input CSV doesn't exist
        if not input_file.exists():
            continue
        
        # Parses through input CSV rows and returns something like [{"organizations": {"id": "1", "name": "Blueprint"}}, ...]
        input_rows = parse_input_csv(str(input_file), input_name)

        # Parses the mapping file into a nested structure 
        mapping = parse_nested_mapping(str(mapping_file), input_name)

        objects = [] # Converted object list

        for row in input_rows:
            mapped_dictionary = nested_map(row, mapping) # Maps to transform flat CSV into nested dictionary
            objects.append(mapped_dictionary)

        results.append((object_type, objects)) # Adds tuple of object type and list of dictionaries. For example: ("organization", [{x}, {y}, ...])

    return results