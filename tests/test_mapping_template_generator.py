from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.lib.generate_mapping import flatten_schema, write_mapping_template_csv
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
            "details.summary",
            "details.notes",
            "contacts[].email",
            "contacts[].phone",
            "contacts[].addresses[].line1",
        ]
        self.assertEqual(paths, expected)

        required = {row.path: row.required for row in rows}
        self.assertTrue(required["id"])
        self.assertTrue(required["details"])
        self.assertTrue(required["details.summary"])
        self.assertFalse(required["name"])
        self.assertFalse(required["details.notes"])
        self.assertFalse(required["contacts[].email"])

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


    def test_flatten_schema_filters_attributes_and_array_container_rows(self) -> None:
        """Test filtering of attributes[] and generic array container rows."""
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

        # Should include attributes[].value
        self.assertIn("attributes[].value", paths)
        # Should NOT include attributes[] container rows
        self.assertNotIn("attributes[]", paths)
        # Should NOT include other attributes sub-fields
        self.assertNotIn("attributes[].id", paths)
        self.assertNotIn("attributes[].label", paths)
        self.assertNotIn("attributes[].url", paths)

        # Should NOT include metadata[] container rows
        self.assertNotIn("metadata[]", paths)
        # Metadata child rows should still be included
        self.assertIn("metadata[].id", paths)
        self.assertIn("metadata[].value", paths)

        # Regular fields should still be included
        self.assertIn("id", paths)
        self.assertIn("regular_field", paths)

    def test_flatten_schema_filters_nested_attributes_and_array_container_rows(self) -> None:
        """Test that nested array containers are filtered but child rows remain."""
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

        # Nested attributes[].value should be included
        self.assertIn("service.attributes[].value", paths)
        # Nested attributes[] container rows should be excluded
        self.assertNotIn("service.attributes[]", paths)
        # Other nested attributes sub-fields should be excluded
        self.assertNotIn("service.attributes[].id", paths)
        self.assertNotIn("service.attributes[].label", paths)

        # Nested metadata[] container rows should be excluded
        self.assertNotIn("service.metadata[]", paths)
        # Nested metadata child rows should still be present
        self.assertIn("service.metadata[].id", paths)
        self.assertIn("service.metadata[].value", paths)

        # Regular fields should still work
        self.assertIn("id", paths)
        self.assertIn("service", paths)
        self.assertIn("service.name", paths)

    def test_referenced_schema_keeps_children_but_skips_array_container_rows(self) -> None:
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
        self.assertIn("contacts[].email", paths)
        self.assertNotIn("contacts[].addresses[]", paths)
        self.assertIn("contacts[].addresses[].city", paths)

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
