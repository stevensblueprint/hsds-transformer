from ..lib.mapper import nested_map, get_process_order
from ..lib.parser import parse_input_csv, parse_nested_mapping
import json
import click
import os

@click.command()
@click.argument('input_file', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.argument('mapping_file', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))

def main(input_file, mapping_file):
    """ TO DO: 
        If field is empty don't include it.
        Multiple CSVs.
        More thorough error handling.
    """
    
    input_filename = os.path.splitext(os.path.basename(input_file))[0]

    src_objects = parse_input_csv(input_file, input_filename)
    mapping = parse_nested_mapping(mapping_file, input_filename)


    # for testing
    # print(mapping)
    # print(src_objects[0])

    output = nested_map(src_objects[0], mapping)
    print(json.dumps(output, indent=2))

    # Testing for get_process_order
    """
    print(get_process_order([
        ("organization", []),
        ("service", []),
        ("address", []),
        ("service_at_location", []),
        ("location", []),
        ("metadata", []),
        ("service_capacity", [])
    ]))

    print(get_process_order([
        ("langauge", []),
        ("organization", []),
        ("phone", []),
        ("location", []),
        ("program", []),
        ("service_at_location", []),
        ("schedule", []),
        ("service", []),
    ]))
    """

if __name__ == "__main__":
    main()
