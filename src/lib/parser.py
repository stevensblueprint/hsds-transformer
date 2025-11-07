import csv
import os

def parse_input_csv(input_file, filename) -> list:
    """
    Takes a csv file and return a list of dictionaries of the form: 
    [{"organization" : { "columns": "value"}}], where every dictionary is a row
    """
    with open(input_file, mode='r', newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        
        filename = os.path.splitext(os.path.basename(input_file))[0]

        input = []
        for row in reader:
            input.append({filename: dict(row)})

    return input

def parse_mapping(mapping_file, filename) -> dict:
    """
    Takes a mapping csv file and return a dictionary of the form: 
    [{"output_field": {"path": "filename.orginal_field}}]
    """
    with open(mapping_file, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)

        next(reader)
        
        mapping = {}
        for row in reader:
            if row[2]:
                mapping[row[1]] = {"path": filename + "." + row[0], "split": row[2]}
            else:
                mapping[row[1]] = {"path": filename + "." + row[0]}

    return mapping

def parse_nested_mapping(mapping_file, filename) -> dict:
    """
    Takes a mapping csv file with paths as keys and returns a dictionary.
    """
    mapping = {}

    # Open and read CSV file
    with open(mapping_file, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader) # Skip header row

        # Process each row of the CSV file
        for row in reader:
            # First column is the desired output path, e.g. "locations[].address"
            path = row[0]
            # Second column is the field from the input file, e.g. "address"
            input_field = row[1]
            split_val = row[2].strip() if len(row) > 2 else ""

            # Skip the row if the input field is empty
            if not input_field:
                continue

            # Build the mapping object we'll attach at the leaf
            map_obj = {"path": f"{filename}.{input_field}"}
            if split_val:
                map_obj["split"] = split_val
            
            # Split the path into parts
            parts = path.split('.')
            current_level = mapping # Start with top level of output dictionary

            # Loop through each part of the path to create the nested structure
            for i, part in enumerate(parts):
                is_last = (i == len(parts) - 1)

                # Case A: The path part indicates a list through "[]"
                if part.endswith('[]'):
                    key = part[:-2] # Remove the "[]" to get the key name
                    
                    # If this is the last part, store a list whose single element is the leaf mapping
                    if is_last:
                        current_level[key] = [map_obj]
                    else:
                        # Initialize the list if it doesn't exist
                        if key not in current_level:
                            current_level[key] = [{}]

                        # Move the pointer of the dictionary inside the list
                        current_level = current_level[key][0]

                # Case B: The path part is a standard dictionary key
                else:
                    key = part
                    # Set the final value if it's the last part of the path
                    if is_last:
                        current_level[key] = map_obj
                    
                    # Go one level deepder if it's not the last part of the path
                    else:
                        current_level = current_level.setdefault(key, {})
    print(mapping)
    return mapping

