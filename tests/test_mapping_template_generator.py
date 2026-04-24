from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.lib.maintenance.generate_mapping import flatten_schema, write_mapping_template_csv
from src.lib.maintenance.parse_json import fetch_json_from_url

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class MappingTemplateGeneratorTests(unittest.TestCase):
    def test_flatten_schema_paths_and_required(self) -> None:
        schema = json.loads((FIXTURES / "sample_schema.json").read_text(encoding="utf-8"))
        rows = flatten_schema(schema)

        paths = [row.path for row in rows]
        expected = [
            "id",
            "name",
            "details",
        ]
        self.assertEqual(paths, expected)

        required = {row.path: row.required for row in rows}
        self.assertTrue(required["id"])
        self.assertTrue(required["details"])
        self.assertFalse(required["name"])

    def test_writer_matches_golden_fixture(self) -> None:
        schema = json.loads((FIXTURES / "sample_schema.json").read_text(encoding="utf-8"))
        rows = flatten_schema(schema)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "sample_mapping_template.csv"
            write_mapping_template_csv(rows, str(out_path))

            expected_lines = (FIXTURES / "sample_mapping_template.csv").read_text(
                encoding="utf-8"
            )
            actual_lines = out_path.read_text(encoding="utf-8")

        self.assertEqual(actual_lines, expected_lines)


    def test_flatten_schema_defaults_to_root_fields_and_attributes_value(self) -> None:
        """Default output keeps root fields plus attributes[].value only."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Identifier"},
                "attributes": {
                    "type": "array",
                    "description": "Attributes",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "ID"},
                            "value": {"type": "string", "description": "Value"},
                            "label": {"type": "string", "description": "Label"},
                            "url": {"type": "string", "description": "URL"},
                        },
                    },
                },
                "metadata": {
                    "type": "array",
                    "description": "Metadata",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "ID"},
                            "value": {"type": "string", "description": "Value"},
                        },
                    },
                },
                "regular_field": {"type": "string", "description": "Regular field"},
            },
        }

        rows = flatten_schema(schema)
        paths = [row.path for row in rows]

        # Should include the allowed attributes[].value exception
        self.assertIn("attributes[].value", paths)

        # Should NOT include array container rows or other bracketed children
        self.assertNotIn("attributes[]", paths)
        self.assertNotIn("attributes[].id", paths)
        self.assertNotIn("attributes[].label", paths)
        self.assertNotIn("attributes[].url", paths)
        self.assertNotIn("metadata[]", paths)
        self.assertNotIn("metadata[].id", paths)
        self.assertNotIn("metadata[].value", paths)

        # Regular fields should still be included
        self.assertIn("id", paths)
        self.assertIn("regular_field", paths)

    def test_flatten_schema_default_excludes_nested_children(self) -> None:
        """Default output does not include nested children or bracketed paths."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "service": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "attributes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "value": {"type": "string"},
                                    "label": {"type": "string"},
                                },
                            },
                        },
                        "metadata": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "value": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        }

        rows = flatten_schema(schema)
        paths = [row.path for row in rows]

        # Nested children and bracketed paths should be excluded
        self.assertNotIn("service.attributes[].value", paths)
        self.assertNotIn("service.attributes[]", paths)
        self.assertNotIn("service.attributes[].id", paths)
        self.assertNotIn("service.attributes[].label", paths)
        self.assertNotIn("service.metadata[]", paths)
        self.assertNotIn("service.metadata[].id", paths)
        self.assertNotIn("service.metadata[].value", paths)

        # Regular fields should still work
        self.assertIn("id", paths)
        self.assertIn("service", paths)
        self.assertNotIn("service.name", paths)

    def test_referenced_schema_keeps_array_descendants_but_filters_array_rows(self) -> None:
        documents = {
            "https://example.com/schema/organization.json": {
                "name": "organization",
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Identifier"},
                    "attributes": {
                        "type": "array",
                        "items": {"$ref": "attribute.json"},
                    },
                    "contacts": {
                        "type": "array",
                        "items": {"$ref": "contact.json"},
                    },
                },
            },
            "https://example.com/schema/attribute.json": {
                "type": "object",
                "properties": {
                    "value": {"type": "string", "description": "Attribute value"},
                    "label": {"type": "string", "description": "Label"},
                },
            },
            "https://example.com/schema/contact.json": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Email"},
                    "addresses": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string", "description": "City"}
                            },
                        },
                    },
                },
            },
        }

        class _FakeResponse:
            def __init__(self, payload, url):
                self._payload = payload
                self.url = url

            def raise_for_status(self) -> None:
                return None

            def json(self):
                return self._payload

        def _fake_get(url: str, *, headers: dict[str, str], timeout: int) -> _FakeResponse:
            return _FakeResponse(documents[url], url)

        with patch("src.lib.maintenance.parse_json.requests.get", _fake_get):
            schema = fetch_json_from_url("https://example.com/schema/organization.json")

        paths = [row.path for row in flatten_schema(schema)]

        self.assertIn("id", paths)
        self.assertIn("attributes[].value", paths)
        self.assertNotIn("attributes[]", paths)
        self.assertNotIn("contacts[]", paths)
        self.assertNotIn("contacts[].email", paths)
        self.assertNotIn("contacts[].addresses[]", paths)
        self.assertNotIn("contacts[].addresses[].city", paths)

    def test_compiled_and_referenced_schemas_produce_same_mapping_paths(self) -> None:
        documents = {
            "https://example.com/schema/organization.json": {
                "name": "organization",
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "attributes": {
                        "type": "array",
                        "items": {"$ref": "attribute.json"},
                    },
                    "contacts": {
                        "type": "array",
                        "items": {"$ref": "contact.json"},
                    },
                },
            },
            "https://example.com/schema/attribute.json": {
                "type": "object",
                "properties": {
                    "value": {"type": "string"},
                    "label": {"type": "string"},
                },
            },
            "https://example.com/schema/contact.json": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "addresses": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                        },
                    },
                },
            },
        }

        compiled_schema = {
            "name": "organization",
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "attributes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "string"},
                            "label": {"type": "string"},
                        },
                    },
                },
                "contacts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "addresses": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {"city": {"type": "string"}},
                                },
                            },
                        },
                    },
                },
            },
        }

        class _FakeResponse:
            def __init__(self, payload, url):
                self._payload = payload
                self.url = url

            def raise_for_status(self) -> None:
                return None

            def json(self):
                return self._payload

        def _fake_get(url: str, *, headers: dict[str, str], timeout: int) -> _FakeResponse:
            return _FakeResponse(documents[url], url)

        with patch("src.lib.maintenance.parse_json.requests.get", _fake_get):
            referenced_schema = fetch_json_from_url("https://example.com/schema/organization.json")

        referenced_paths = [row.path for row in flatten_schema(referenced_schema)]
        compiled_paths = [row.path for row in flatten_schema(compiled_schema)]

        self.assertEqual(referenced_paths, compiled_paths)


if __name__ == "__main__":
    unittest.main()
