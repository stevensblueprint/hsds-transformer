# from ..lib.mapper import get_process_order
from ..lib.outputs import save_objects_to_json
from ..lib.collections import build_collections, searching_and_assigning
import json
import click
import sys

@click.command()
@click.argument('data_dictionary', type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True))
@click.option('--output-dir', '-o', default='output', help='Output directory for JSON files')

def main(data_dictionary, output_dir):
    """ TO DO: 
        If field is empty don't include it.
        Multiple CSVs.
        More thorough error handling.
    """

    try:
        results = build_collections(data_dictionary) # Builds collections
        results = searching_and_assigning(results) # Links and cleans up
        
        # Save individual JSON files
        save_objects_to_json(results, output_dir)
        
        output_json = json.dumps(results, indent=2, ensure_ascii=False) # Convert to json string
        click.echo(output_json)

    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {str(e)}", err=True)
        sys.exit(1)

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
