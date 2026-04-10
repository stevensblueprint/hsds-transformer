import json
from copy import deepcopy
from typing import Any
from urllib.parse import urldefrag, urljoin

import requests


SCHEMA_URL = "https://raw.githubusercontent.com/openreferral/specification/refs/heads/3.2/schema/compiled/organization.json"


def _fetch_document(url: str, *, timeout_s: int, cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if url in cache:
        return cache[url]

    headers = {
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
        raise ValueError(f"Response from {url!r} was not valid JSON: {e}") from e

    if not isinstance(parsed, dict):
        raise TypeError(f"Expected top-level JSON object (dict), got {type(parsed).__name__}")

    cache[url] = parsed
    return parsed


def _decode_json_pointer_part(part: str) -> str:
    return part.replace("~1", "/").replace("~0", "~")


def _resolve_json_pointer(document: Any, fragment: str) -> Any:
    if not fragment or fragment == "#":
        return document
    if not fragment.startswith("#"):
        raise ValueError(f"Unsupported JSON pointer fragment: {fragment!r}")

    pointer = fragment[1:]
    if not pointer:
        return document
    if not pointer.startswith("/"):
        raise ValueError(f"Unsupported JSON pointer fragment: {fragment!r}")

    current = document
    for raw_part in pointer.split("/")[1:]:
        part = _decode_json_pointer_part(raw_part)
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(f"JSON pointer {fragment!r} not found")
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
            except ValueError as e:
                raise KeyError(f"JSON pointer {fragment!r} not found") from e
            try:
                current = current[index]
            except IndexError as e:
                raise KeyError(f"JSON pointer {fragment!r} not found") from e
        else:
            raise KeyError(f"JSON pointer {fragment!r} not found")
    return current


def _dereference_node(
    node: Any,
    *,
    document_url: str,
    timeout_s: int,
    cache: dict[str, dict[str, Any]],
    resolving: set[str],
) -> Any:
    if isinstance(node, list):
        return [
            _dereference_node(
                item,
                document_url=document_url,
                timeout_s=timeout_s,
                cache=cache,
                resolving=resolving,
            )
            for item in node
        ]

    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        ref = node["$ref"]
        if not isinstance(ref, str):
            raise TypeError(f"Expected $ref to be a string, got {type(ref).__name__}")

        ref_url, fragment = urldefrag(urljoin(document_url, ref))
        target_url = ref_url or document_url
        ref_key = f"{target_url}#{fragment}" if fragment else target_url
        if ref_key in resolving:
            raise ValueError(f"Circular $ref detected: {ref_key}")

        resolving.add(ref_key)
        target_document = _fetch_document(target_url, timeout_s=timeout_s, cache=cache)
        resolved_target = _resolve_json_pointer(target_document, f"#{fragment}" if fragment else "#")
        resolved = _dereference_node(
            deepcopy(resolved_target),
            document_url=target_url,
            timeout_s=timeout_s,
            cache=cache,
            resolving=resolving,
        )
        resolving.remove(ref_key)

        sibling_keys = {k: v for k, v in node.items() if k != "$ref"}
        if sibling_keys:
            sibling_values = _dereference_node(
                sibling_keys,
                document_url=document_url,
                timeout_s=timeout_s,
                cache=cache,
                resolving=resolving,
            )
            if not isinstance(resolved, dict):
                raise TypeError("Cannot merge $ref siblings into a non-object target")
            merged = dict(resolved)
            merged.update(sibling_values)
            return merged

        return resolved

    return {
        key: _dereference_node(
            value,
            document_url=document_url,
            timeout_s=timeout_s,
            cache=cache,
            resolving=resolving,
        )
        for key, value in node.items()
    }


def fetch_json_from_url(url: str, *, timeout_s: int = 30) -> dict[str, Any]:
    """
    Fetch and parse a dereferenced JSON Schema into a Python dictionary.

    Args:
        url: The URL of the JSON Schema to fetch and dereference.
        timeout_s: Timeout in seconds for each HTTP request while fetching
            schema documents.

    Returns:
        A dictionary representing the dereferenced JSON Schema.

    """
    parsed = _fetch_document(url, timeout_s=timeout_s, cache={})
    dereferenced = _dereference_node(
        deepcopy(parsed),
        document_url=url,
        timeout_s=timeout_s,
        cache={url: parsed},
        resolving=set(),
    )
    if not isinstance(dereferenced, dict):
        raise TypeError(f"Expected top-level JSON object (dict), got {type(dereferenced).__name__}")
    return dereferenced

if __name__ == "__main__":
    schema = fetch_json_from_url(SCHEMA_URL)

    #print full dictionary
    print(f"Loaded schema dict with keys: {sorted(schema.keys())} \n full dictionary: {json.dumps(schema, indent=2, ensure_ascii=False)}")

    # print first 20 lines of the dictionary (debug)
    pretty = json.dumps(schema, indent=2, ensure_ascii=False)
    first_20_lines = "\n".join(pretty.splitlines()[:20])
    print(first_20_lines)
