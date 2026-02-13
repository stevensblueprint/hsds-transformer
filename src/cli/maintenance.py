import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import click

from src.lib.maintenance.parse_json import fetch_json_from_url
from src.lib.generate_mapping import flatten_schema, write_mapping_template_csv


# url validation checking
def _validate_url(url, valid_urls):
    valid_hostnames = {h.strip().lower() for h in valid_urls.split(",") if h.strip()}

    parsed = urlparse(url)

    hostname = (parsed.hostname or "").lower()
    url_elements = [parsed.scheme, parsed.path]
    if hostname:
        url_elements.append(hostname)

    if not all(url_elements):
        raise click.ClickException("Invalid URL Provided")
    else:
        if (
            (parsed.scheme not in ["http", "https"])
            or (hostname not in valid_hostnames)
            or (_path_ext(parsed.path) != "json")
        ):
            raise click.ClickException("Invalid URL Provided")


def _path_ext(path):
    return (path.split(".")[-1]).lower() if "." in path else ""


def _sanitize_stem(value: str) -> str:
    sanitized = value.strip().replace(" ", "_")
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", sanitized)
    sanitized = sanitized.strip("._-")
    if not sanitized:
        return ""
    return sanitized.lower()


def _output_filename(url: str, schema: dict) -> str:
    """Derive an output CSV filename from the schema name or URL."""
    name = schema.get("name")
    if name and isinstance(name, str):
        stem = _sanitize_stem(name)
    else:
        stem = ""

    if not stem:
        # Fall back to the URL filename without extension
        stem = _sanitize_stem(PurePosixPath(urlparse(url).path).stem) or "mapping_template"

    return f"{stem}_mapping_template.csv"


def _resolve_output_path(filename: str) -> Path:
    cwd = Path.cwd().resolve()
    output_path = (cwd / filename).resolve()
    if output_path.parent != cwd:
        raise click.ClickException("Unsafe output path generated from schema name")
    return output_path


@click.group()
def main():
    pass


# subcommand generate mapping
@main.command()
@click.option(
    "--github-url",
    type=click.STRING,
    required=True,
    help="Github URL for Json Schema",
)
@click.option(
    "--valid-hostname",
    type=click.STRING,
    default="github.com,raw.githubusercontent.com",
    help="Valid Hostnames for URL",
)
def generate_mapping(github_url, valid_hostname):
    _validate_url(github_url, valid_hostname)

    out_file: Path | None = None
    try:
        click.echo("Fetching schema...")
        schema = fetch_json_from_url(github_url)

        click.echo("Generating mapping template...")
        rows = flatten_schema(schema)
        if not rows:
            raise click.ClickException("Schema produced no mapping fields")

        out_file = _resolve_output_path(_output_filename(github_url, schema))
        if out_file.exists():
            raise click.ClickException(
                f"Output file already exists: {out_file}. Remove it and run again."
            )

        write_mapping_template_csv(rows, str(out_file))
    except click.ClickException:
        raise
    except FileExistsError as exc:
        output_name = str(out_file) if out_file is not None else "mapping template"
        raise click.ClickException(
            f"Output file already exists: {output_name}. Remove it and run again."
        ) from exc
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Mapping template written to {out_file} ({len(rows)} fields)")


if __name__ == "__main__":
    main()
