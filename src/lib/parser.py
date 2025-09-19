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
            mapping[row[1]] = {"path": filename + "." + row[0]}

    return mapping

def parse_nested_mapping(mapping_file, filename) -> dict:
    """
    Takes a mapping csv file with paths as keys and returns a dictionary.
    """
    mapping = {}

    return mapping

