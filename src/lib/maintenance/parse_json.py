import json
from typing import Any
import requests


SCHEMA_URL = "https://raw.githubusercontent.com/openreferral/specification/refs/heads/3.2/schema/compiled/organization.json"


def fetch_json_from_url(url: str, *, timeout_s: int = 30) -> dict[str, Any]:
    """
    Fetch and parse a dereferenced JSON Schema into a Python dictionary.

    The schema URL is hard-coded for now
    
    Args:
        url: The URL of the JSON Schema to fetch
        timeout_s: The timeout in seconds for the request

    Returns:
        A dictionary of the JSON Schema

    """
    headers = {
        # Explicit User-Agent to prevent potentially failed requests
        "User-Agent": "hsds-transformer/parse_json",
        "Accept": "application/json",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout_s)
        resp.raise_for_status()
        parsed = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch JSON from {url!r}: {e}") from e
    except ValueError as e:
        # requests raises ValueError on JSON decode errors.
        raise ValueError(f"Response from {url!r} was not valid JSON: {e}") from e

    if not isinstance(parsed, dict):
        raise TypeError(f"Expected top-level JSON object (dict), got {type(parsed).__name__}")

    return parsed

if __name__ == "__main__":
    schema = fetch_json_from_url(SCHEMA_URL)

    #print full dictionary
    print(f"Loaded schema dict with keys: {sorted(schema.keys())} \n full dictionary: {json.dumps(schema, indent=2, ensure_ascii=False)}")

    # print first 20 lines of the dictionary (debug)
    pretty = json.dumps(schema, indent=2, ensure_ascii=False)
    first_20_lines = "\n".join(pretty.splitlines()[:20])
    print(first_20_lines)