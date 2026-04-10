from __future__ import annotations

from typing import Any

import pytest

from src.lib.maintenance.parse_json import fetch_json_from_url


class _FakeResponse:
    def __init__(self, payload: Any):
        self._payload = payload

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
        return _FakeResponse(documents[url])

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
        return _FakeResponse(document)

    monkeypatch.setattr("src.lib.maintenance.parse_json.requests.get", _fake_get)

    schema = fetch_json_from_url("https://example.com/schema/location.json")

    assert schema["properties"]["attributes"]["items"]["properties"]["value"]["description"] == "Attribute value"
    assert "$ref" not in schema["properties"]["attributes"]["items"]
