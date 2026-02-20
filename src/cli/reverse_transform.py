from pathlib import Path
import click
from ..lib.reverse_transform.reverse_transform import process_mappings, get_entity_objects, ingest_json_directory
from ..lib.reverse_transform.buildcsv import reverseTransform

def _ensure_non_empty_dir(path: Path, label: str) -> None:
    if not any(path.iterdir()):
        raise click.ClickException(f"{label} directory '{path}' is empty.")


def _find_files(path: Path, pattern: str, label: str) -> list[Path]:
    files = list(path.glob(pattern))
    if not files:
        raise click.ClickException(f"No {label} files found in '{path}'.")
    return files


@click.command()
@click.option(
    "--mapping-dir",
    "-m",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    help="Directory containing mapping CSV files.",
)
@click.option(
    "--hsds-dir",
    "-i",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    help="Directory containing HSDS JSON files.",
)
@click.option(
    "--output-dir",
    "-o",
    default="reverse_output",
    show_default=True,
    help="Output directory for reversed CSV files.",
)
def main(mapping_dir: str, hsds_dir: str, output_dir: str) -> None:
    mapping_path = Path(mapping_dir)
    hsds_path = Path(hsds_dir)
    output_path = Path(output_dir)

    _ensure_non_empty_dir(mapping_path, "Mapping")
    _ensure_non_empty_dir(hsds_path, "HSDS")

    csv_files = _find_files(mapping_path, "*.csv", "CSV")
    json_files = _find_files(hsds_path, "*.json", "JSON")

    click.echo(
        f"Found {len(csv_files)} mapping CSV file(s) and {len(json_files)} HSDS JSON file(s)."
    )
    click.echo(f"Output directory: {output_dir}")

    mapping_data = process_mappings(mapping_path)
    all_objects = ingest_json_directory(hsds_path)

    output_path.mkdir(parents=True, exist_ok=True)
    for spec in mapping_data:
        dict_list = get_entity_objects(spec, all_objects, hsds_path)
        if dict_list is None:
            click.echo(f"  Skipping {spec.source_file.name}: unrecognized mapping filename format.")
            continue

        output_file = output_path / f"{spec.name}.csv"
        click.echo(f"  Writing {output_file.name} ({len(dict_list)} row(s))...")
        reverseTransform(
            dictList=dict_list,
            pathsTuple=spec.fields,
            csvPath=output_file,
        )

    click.echo(f"Done. {len(mapping_data)} CSV file(s) written to '{output_path}'.")
if __name__ == "__main__":
    main()
