import click
import csv
import os

@click.command()
@click.argument('input_file', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.argument('mapping_file', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))

def main(input_file, mapping_file):
    """Reads a CSV file from the given path and prints its content."""
    """If field is empty don't include it."""
    
    with open(input_file, mode='r', newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        
        filename = os.path.splitext(input_file)[0]

        result = []
        for row in reader:
            result.append({filename: dict(row)})

    print(result[0])
        
    # print(csv_to_key_value_dict(mapping_file))

def create_object(column_names, row, file_name):
    pass

def csv_to_key_value_dict(file_path):
    """Convert 2-column CSV to key-value dictionary"""
    result = {}
    with open(file_path, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) >= 2:
                result[row[0]] = row[1]
    return result

if __name__ == "__main__":
    main()
