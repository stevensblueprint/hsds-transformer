from pathlib import Path

from ..lib.transform.outputs import save_objects_to_json
from ..lib.transform.collections import build_collections, searching_and_assigning
from ..lib.transform.json_collections import build_collections_from_json
from ..lib.transform.logger import transformer_log
from ..lib.custom_transform.transforms_loader import load_transforms_registry_if_available
import click
import sys

@click.command()
@click.argument('data_dictionary', type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True))
@click.option('--output-dir', '-o', default='output', help='Output directory for JSON files')
@click.option('--generate-ids', default=None, help='Generate new IDs using the provided organization name/id')
@click.option('--input-format', '-f', type=click.Choice(['csv', 'json'], case_sensitive=False), default='csv', help='Input data format (csv or json)')
@click.option(
    '--transforms',
    type=click.Path(exists=False, dir_okay=False, file_okay=True, path_type=Path),
    default=None,
    help='Path to a Python module defining custom transforms (optional; omitted or missing file runs without them)',
)

def main(data_dictionary, output_dir, generate_ids, transforms, input_format):
    try:
        # Clear any previous log entries from prior runs
        transformer_log.clear()

        # Build collections from the specified input format
        if input_format == 'json':
            results = build_collections_from_json(data_dictionary)
        else:
            results = build_collections(data_dictionary)

        transforms_registry = load_transforms_registry_if_available(transforms)
        if transforms is None:
            transformer_log.log("Custom transforms: not used (no --transforms path).")
        elif transforms_registry is None:
            transformer_log.log(
                f"Custom transforms: not used (path not found or not a file: {transforms})."
            )
        else:
            transformer_log.log(
                f"Custom transforms: loaded from {transforms.resolve()}."
            )
            
        results = searching_and_assigning(results, requestor_identifier=generate_ids) # Links and cleans up, passes transformer_id

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
