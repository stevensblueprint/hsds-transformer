from ..lib.collections import build_collections, searching_and_assigning
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
    results = searching_and_assigning(results) # Links and cleans up

    output_json = json.dumps(results, indent=2, ensure_ascii=False) # Convert to json string

    click.echo(output_json)

if __name__ == "__main__":
    main()
