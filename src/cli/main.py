from ..lib.outputs import save_objects_to_json
from ..lib.collections import build_collections, searching_and_assigning
from ..lib.logger import transformer_log
import json
import click
import sys

@click.command()
@click.argument('data_dictionary', type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True))
@click.option('--output-dir', '-o', default='output', help='Output directory for JSON files')

def main(data_dictionary, output_dir):
    try:
        # Clear any previous log entries from prior runs
        transformer_log.clear()
        
        results = build_collections(data_dictionary) # Builds collections
        results = searching_and_assigning(results) # Links and cleans up
        
        # Save individual JSON files
        save_objects_to_json(results, output_dir)
        
        # Log output summary
        transformer_log.section("Output")
        transformer_log.log(f"JSON files saved to: {output_dir}")
        
        # Print the log instead of results
        click.echo(transformer_log.get_log())

    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
