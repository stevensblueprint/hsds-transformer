from __future__ import annotations

import json
from pathlib import Path

import click

from ..lib.mapping_template import flatten_schema, write_mapping_template_csv


def _derive_output_name(schema: dict, schema_path: Path) -> str:
    raw_name = schema.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    base = name if name else schema_path.stem
    return f"{base}_mapping_template.csv"


@click.command(
    help=(
        "Generate a mapping-template CSV from a dereferenced HSDS JSON schema file. "
        "The schema must already be dereferenced and stored locally as a JSON object."
    ),
    epilog=(
        "Output CSV format: header row, empty second row, then one row per schema path. "
        "Array paths use [] (e.g., contacts[].phones[].number)."
    ),
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--schema-file",
    "-s",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help=(
        "Path to a local, dereferenced HSDS JSON schema file. "
        "This command does not fetch URLs or resolve $ref."
    ),
)
@click.option(
    "--out",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    help=(
        "Output CSV path. Defaults to <schema_name>_mapping_template.csv, "
        "falling back to <schema_file_stem>_mapping_template.csv if schema name is missing."
    ),
)
def main(schema_file: Path, out: Path | None) -> None:
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(
            f"Schema file '{schema_file}' does not contain valid JSON: {exc}"
        ) from exc

    if not isinstance(schema, dict):
        raise click.ClickException("Schema JSON must be an object.")

    output_path = out if out is not None else Path(_derive_output_name(schema, schema_file))
    rows = flatten_schema(schema)
    write_mapping_template_csv(rows, str(output_path))

    click.echo(f"Wrote mapping template to {output_path}")


if __name__ == "__main__":
    main()
