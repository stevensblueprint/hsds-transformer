# from ..lib.mapper import get_process_order
from ..lib.collections import build_collections
import json
import click

@click.command()
@click.argument('data_dictionary', type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True))

def main(data_dictionary):
    """ TO DO: 
        If field is empty don't include it.
        Multiple CSVs.
        More thorough error handling.
    """

    results = build_collections(data_dictionary) # Builds collections

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
