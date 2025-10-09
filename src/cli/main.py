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

if __name__ == "__main__":
    main()
