import click
import requests
from urllib.parse import urlparse


# url validation checking
def _validate_url(url, valid_urls):
        urlList = [h.strip().lower() for h in valid_urls.split(',') if h.strip()]

        parsed = urlparse(url)

        hostname = (parsed.netloc or "")
        urlElements = [parsed.scheme,parsed.path]
        if hostname:
            urlElements.append(hostname)
        
        if not all(urlElements) :
            raise click.ClickException("Invalid URL Provided")
        else:
            if ((parsed.scheme not in ['http','https'])) or ((hostname not in urlList)) or (_path_ext(parsed.path) != 'json'):
                raise click.ClickException("Invalid URL Provided")

def _post_url(url):
    try:
        request = requests.get(url, timeout=10)
        if request.status_code != 200: 
            raise click.ClickException("Url Unreachable")
    except requests.RequestException as exc:
        raise click.ClickException("URL Unreachable") from exc
def _path_ext(path):
    return (path.split('.')[-1]).lower() if '.' in path else ''



@click.group()
def main():
    pass

# subcommand generate mapping
@main.command()
@click.option(
    '--github-url',
    type=click.STRING,
    required=True,
    help="Github URL for Json Schema"
)
@click.option(
    "--valid-hostname",
    type=click.STRING,
    default="github.com,raw.githubusercontent.com",
    help="Valid Hostnames for URL"
)
def generate_mapping(github_url, valid_hostname):
    _validate_url(github_url,valid_hostname)
    _post_url(github_url)
    click.echo("Valid url, JSON Schema is reachable, mapping generation not yet implemented")


if __name__ == "__main__":
    main()

