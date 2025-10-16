# from ..lib.mapper import get_process_order
from ..lib.collections import build_collections
from ..lib.outputs import save_objects_to_json
import json
import click

@click.command()
@click.argument('data_dictionary', type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True))
@click.option('--output-dir', '-o', default='output', help='Output directory for JSON files')

def main(data_dictionary, output_dir):
    """ TO DO: 
        If field is empty don't include it.
        Multiple CSVs.
        More thorough error handling.
    """

    results = build_collections(data_dictionary) # Builds collections

    # Save individual JSON files
    save_objects_to_json(results, output_dir)

    output_json = json.dumps(results, indent=2, ensure_ascii=False) # Convert to json string

    click.echo(output_json)

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
