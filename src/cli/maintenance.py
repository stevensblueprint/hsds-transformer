import click
import requests
from urllib.parse import urlparse


# url validation checking
def _validate_url(url, valid_urls):
        urlList = valid_urls.split(',')

        parsed = urlparse(url)
        urlElements = [parsed.scheme, parsed.path]
        if parsed.netloc != "":
            urlElements.append(parsed.netloc)
        
        if not all(urlElements) :
            raise click.ClickException("Invalid URL Provided")
        else:
            if ((parsed.scheme not in ['http','https'])) or ((parsed.netloc not in urlList)) or (_path_ext(parsed.path) != 'json'):
                raise click.ClickException("Invalid URL Provided")

def _post_url(url):
    request = requests.get(url)
    if request.status_code != 200: 
        raise click.ClickException("Url Unreachable")

def _path_ext(path):
    return (path.split('.')[-1])



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
@click.option(
    '--check-connectivity',
    is_flag=True
)
def generate_mapping(github_url, valid_hostname, check_connectivity):
    _validate_url(github_url,valid_hostname)
    if check_connectivity:
        _post_url(github_url)

    click.echo("Valid url, JSON Schema is reachable, mapping generation not yet implemented")


if __name__ == "__main__":
    main()

