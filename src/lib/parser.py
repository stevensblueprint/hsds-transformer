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
            # Normalize header keys by trimming whitespace
            normalized = { (k.strip() if isinstance(k, str) else k): v for k, v in row.items() }
            input.append({filename: normalized})

    return input

def parse_mapping(mapping_file, filename) -> dict:
    """
    Takes a mapping csv file and return a dictionary of the form: 
    [{"output_field": {"path": "filename.original_field}}]
    """
    with open(mapping_file, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)

        next(reader)
        
        mapping = {}
        for row in reader:
            mapping[row[1]] = {"path": filename + "." + row[0]}

    return mapping

def parse_nested_mapping(mapping_file, filename):
    """
    Takes a mapping CSV file with the following structure and returns a tuple
    of (mapping_dict, filter_spec or None):

    - Row 1: Column headers (ignored by position-based parsing)
    - Row 2: Optional filter row: [column_name_to_check, value_to_match]
             If empty, no filter is applied (returns None for filter)
    - Row 3+: Mapping rows: [output_path, input_field]
    """
    mapping = {}
    filter_spec = None

    with open(mapping_file, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)

        # Row 1: header
        try:
            next(reader)
        except StopIteration:
            return mapping, None

        # Row 2: optional filter row
        try:
            filter_row = next(reader)
        except StopIteration:
            filter_row = None

        if filter_row and len(filter_row) >= 2:
            filter_column = (filter_row[0] or '').strip()
            filter_value = (filter_row[1] or '').strip()
            if filter_column and filter_value:
                filter_spec = {"column": filter_column, "value": filter_value}

        # Row 3+: mapping rows
        for row in reader:
            if not row or len(row) < 2:
                continue

            path = (row[0] or '').strip()
            input_field = (row[1] or '').strip()

            if not path or not input_field:
                continue

            parts = path.split('.')
            current_level = mapping

            for i, part in enumerate(parts):
                is_last = (i == len(parts) - 1)

                if part.endswith('[]'):
                    key = part[:-2]
                    if key not in current_level:
                        current_level[key] = [{}]
                    current_level = current_level[key][0]
                else:
                    key = part
                    if is_last:
                        current_level[key] = {"path": f"{filename}.{input_field}"}
                    else:
                        current_level = current_level.setdefault(key, {})

    return mapping, filter_spec

