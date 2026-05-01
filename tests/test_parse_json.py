from __future__ import annotations

from typing import Any

import pytest

from src.lib.maintenance.parse_json import fetch_json_from_url


class _FakeResponse:
    def __init__(self, payload: Any, *, url: str | None = None):
        self._payload = payload
        self.url = url or "https://example.com/schema/default.json"

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


def test_fetch_json_from_url_dereferences_relative_refs(monkeypatch: pytest.MonkeyPatch) -> None:
    documents = {
        "https://example.com/schema/organization.json": {
            "name": "organization",
            "type": "object",
            "properties": {
                "attributes": {
                    "type": "array",
                    "items": {"$ref": "attribute.json"},
                }
            },
        },
        "https://example.com/schema/attribute.json": {
            "type": "object",
            "properties": {
                "value": {"type": "string", "description": "Attribute value"},
                "label": {"type": "string", "description": "Attribute label"},
            },
        },
    }
    calls: list[str] = []

    def _fake_get(url: str, *, headers: dict[str, str], timeout: int) -> _FakeResponse:
        assert headers["Accept"] == "application/json"
        assert timeout == 30
        calls.append(url)
        return _FakeResponse(documents[url], url=url)

    monkeypatch.setattr("src.lib.maintenance.parse_json.requests.get", _fake_get)

    schema = fetch_json_from_url("https://example.com/schema/organization.json")

    assert schema["properties"]["attributes"]["items"]["properties"]["value"]["description"] == "Attribute value"
    assert "$ref" not in schema["properties"]["attributes"]["items"]
    assert calls == [
        "https://example.com/schema/organization.json",
        "https://example.com/schema/attribute.json",
    ]


def test_fetch_json_from_url_dereferences_local_fragment_refs(monkeypatch: pytest.MonkeyPatch) -> None:
    document = {
        "definitions": {
            "attribute": {
                "type": "object",
                "properties": {
                    "value": {"type": "string", "description": "Attribute value"}
                },
            }
        },
        "type": "object",
        "properties": {
            "attributes": {
                "type": "array",
                "items": {"$ref": "#/definitions/attribute"},
            }
        },
    }

    def _fake_get(url: str, *, headers: dict[str, str], timeout: int) -> _FakeResponse:
        return _FakeResponse(document, url=url)

    monkeypatch.setattr("src.lib.maintenance.parse_json.requests.get", _fake_get)

    schema = fetch_json_from_url("https://example.com/schema/location.json")

    assert schema["properties"]["attributes"]["items"]["properties"]["value"]["description"] == "Attribute value"
    assert "$ref" not in schema["properties"]["attributes"]["items"]


def test_fetch_json_from_url_uses_redirected_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    documents = {
        "https://example.com/schema/organization.json": _FakeResponse(
            {
                "type": "object",
                "properties": {
                    "attributes": {
                        "type": "array",
                        "items": {"$ref": "attribute.json"},
                    }
                },
            },
            url="https://cdn.example.com/v2/organization.json",
        ),
        "https://cdn.example.com/v2/attribute.json": _FakeResponse(
            {
                "type": "object",
                "properties": {"value": {"type": "string", "description": "Redirected"}},
            },
            url="https://cdn.example.com/v2/attribute.json",
        ),
    }

    def _fake_get(url: str, *, headers: dict[str, str], timeout: int) -> _FakeResponse:
        return documents[url]

    monkeypatch.setattr("src.lib.maintenance.parse_json.requests.get", _fake_get)

    schema = fetch_json_from_url("https://example.com/schema/organization.json")

    assert schema["properties"]["attributes"]["items"]["properties"]["value"]["description"] == "Redirected"


def test_fetch_json_from_url_detects_circular_refs(monkeypatch: pytest.MonkeyPatch) -> None:
    document = {
        "definitions": {
            "a": {"$ref": "#/definitions/b"},
            "b": {"$ref": "#/definitions/a"},
        },
        "type": "object",
        "properties": {"field": {"$ref": "#/definitions/a"}},
    }

    def _fake_get(url: str, *, headers: dict[str, str], timeout: int) -> _FakeResponse:
        return _FakeResponse(document, url=url)

    monkeypatch.setattr("src.lib.maintenance.parse_json.requests.get", _fake_get)

    with pytest.raises(ValueError, match="Circular"):
        fetch_json_from_url("https://example.com/schema/circular.json")


def test_fetch_json_from_url_merges_ref_sibling_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    document = {
        "definitions": {
            "attribute": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
            }
        },
        "type": "object",
        "properties": {
            "attributes": {
                "items": {
                    "$ref": "#/definitions/attribute",
                    "description": "Overridden description",
                }
            }
        },
    }

    def _fake_get(url: str, *, headers: dict[str, str], timeout: int) -> _FakeResponse:
        return _FakeResponse(document, url=url)

    monkeypatch.setattr("src.lib.maintenance.parse_json.requests.get", _fake_get)

    schema = fetch_json_from_url("https://example.com/schema/merge.json")

    assert schema["properties"]["attributes"]["items"]["description"] == "Overridden description"
    assert schema["properties"]["attributes"]["items"]["properties"]["value"]["type"] == "string"


def test_fetch_json_from_url_handles_escaped_json_pointer(monkeypatch: pytest.MonkeyPatch) -> None:
    document = {
        "definitions": {
            "a/b": {
                "tilde~name": {
                    "type": "object",
                    "properties": {"value": {"type": "string", "description": "Escaped"}},
                }
            }
        },
        "type": "object",
        "properties": {
            "field": {"$ref": "#/definitions/a~1b/tilde~0name"},
        },
    }

    def _fake_get(url: str, *, headers: dict[str, str], timeout: int) -> _FakeResponse:
        return _FakeResponse(document, url=url)

    monkeypatch.setattr("src.lib.maintenance.parse_json.requests.get", _fake_get)

    schema = fetch_json_from_url("https://example.com/schema/escaped.json")

    assert schema["properties"]["field"]["properties"]["value"]["description"] == "Escaped"


def test_fetch_json_from_url_errors_when_merging_into_non_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    document = {
        "definitions": {"label": "value"},
        "type": "object",
        "properties": {
            "field": {
                "$ref": "#/definitions/label",
                "description": "Cannot merge onto string",
            }
        },
    }

    def _fake_get(url: str, *, headers: dict[str, str], timeout: int) -> _FakeResponse:
        return _FakeResponse(document, url=url)

    monkeypatch.setattr("src.lib.maintenance.parse_json.requests.get", _fake_get)

    with pytest.raises(TypeError, match="non-object target"):
        fetch_json_from_url("https://example.com/schema/non-dict-merge.json")


def test_fetch_json_from_url_rejects_negative_array_index(monkeypatch: pytest.MonkeyPatch) -> None:
    document = {
        "definitions": [{"type": "string", "description": "first"}],
        "type": "object",
        "properties": {"field": {"$ref": "#/definitions/-1"}},
    }

    def _fake_get(url: str, *, headers: dict[str, str], timeout: int) -> _FakeResponse:
        return _FakeResponse(document, url=url)

    monkeypatch.setattr("src.lib.maintenance.parse_json.requests.get", _fake_get)

    with pytest.raises(KeyError, match="#/definitions/-1"):
        fetch_json_from_url("https://example.com/schema/negative-index.json")
