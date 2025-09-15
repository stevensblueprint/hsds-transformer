from lib.mapper import map
from lib.parser import parse_input_csv, parse_mapping
import click
import csv
import os

@click.command()
@click.argument('input_file', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.argument('mapping_file', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))

def main(input_file, mapping_file):
    """ TO DO: 
        If field is empty don't include it.
        Multiple CSVs.
    """
    
    input_filename = os.path.splitext(os.path.basename(input_file))[0]

    mapping = parse_mapping(mapping_file, input_filename)
    src_objects = parse_input_csv(input_file, input_filename)

    # for testing
    # print(mapping)
    # print(src_objects[0])

    organization = map(src_objects[0], mapping)
    print(organization.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
