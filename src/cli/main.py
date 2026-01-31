from ..lib.outputs import save_objects_to_json
from ..lib.collections import build_collections, searching_and_assigning
import json
import click
import sys

@click.command()
@click.argument('data_dictionary', type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True))
@click.option('--output-dir', '-o', default='output', help='Output directory for JSON files')
@click.option('--parent-org', default=None, help='ID or name of person/organization performing the transformation')

def main(data_dictionary, output_dir, parent_org):
    try:
        results = build_collections(data_dictionary)  # Builds collections
        results = searching_and_assigning(results, requestor_identifier=parent_org) # Links and cleans up, passes transformer_id
        
        # Save individual JSON files
        save_objects_to_json(results, output_dir)
        # Save as a single JSON file
        output_json = json.dumps(results, indent=2, ensure_ascii=False) # Convert to json string
        click.echo(output_json)

    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
