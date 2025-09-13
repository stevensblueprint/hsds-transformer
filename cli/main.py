import click
import csv

@click.command()
@click.argument('input_file', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.argument('mapping_file', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))

def main(input_file, mapping_file):
    """Reads a CSV file from the given path and prints its content."""
    with open(file_path, mode='r', newline='', encoding='utf-8') as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            print(row)
    
    print(csv_to_key_value_dict(mapping_file))

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
