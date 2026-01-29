import click
#import requests
from urllib.parse import *



def _validate_url(url, valid_urls):
    try:
        urlList = valid_urls.split(',')

        parsed = urlparse(url)
        urlComp = [parsed.scheme, parsed.path]
        if parsed.netloc != "":
            urlComp.append(parsed.netloc)
        
        if all(urlComp) == False:
            raise click.ClickException("Invalid URL Provided")
        else:
            if (parsed.scheme in ['http','https']) == False:
                raise click.ClickException("Invalid URL Provided")
            elif (parsed.netloc in urlList) == False:
                raise click.ClickException("Invalid URL Provided")
    except:
        raise click.ClickException("Invalid URL Provided")



@click.group()
def main():
    pass


@main.command()
@click.option('--github-url',type=click.STRING,required=True)
@click.option("--valid-hostname",type=click.STRING,default="github.com,raw.githubusercontent.com")
def generate_mapping(github_url, valid_hostname):
    _validate_url(github_url,valid_hostname)
    click.echo("Valid url, JSON Schema is reachable, mapping generation not yet implemented")

if __name__ == "__main__":
    main()


#https://github.com/SchemaStore/schemastore/blob/master/src/schemas/json/abc-inventory-module-data-5.1.0.json
#https://raw.githubusercontent.com/SchemaStore/schemastore/refs/heads/master/src/schemas/json/abc-inventory-module-data-5.1.0.json