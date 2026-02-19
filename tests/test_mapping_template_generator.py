from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.lib.generate_mapping import flatten_schema, write_mapping_template_csv

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
            "tags[]",
            "contacts[]",
            "contacts[].email",
            "contacts[].phone",
            "contacts[].addresses[]",
            "contacts[].addresses[].line1",
        ]
        self.assertEqual(paths, expected)

        required = {row.path: row.required for row in rows}
        self.assertTrue(required["id"])
        self.assertTrue(required["details"])
        self.assertTrue(required["details.summary"])
        self.assertTrue(required["tags[]"])
        self.assertFalse(required["name"])
        self.assertFalse(required["details.notes"])
        self.assertFalse(required["contacts[]"])
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


    def test_flatten_schema_filters_attributes_and_metadata(self) -> None:
        """Test that attributes[] (except value) and metadata[] fields are filtered out."""
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

        # Should include attributes[] itself
        self.assertIn("attributes[]", paths)
        # Should include attributes[].value
        self.assertIn("attributes[].value", paths)
        # Should NOT include other attributes sub-fields
        self.assertNotIn("attributes[].id", paths)
        self.assertNotIn("attributes[].label", paths)
        self.assertNotIn("attributes[].url", paths)

        # Should NOT include metadata[] or any of its children
        self.assertNotIn("metadata[]", paths)
        self.assertNotIn("metadata[].id", paths)
        self.assertNotIn("metadata[].value", paths)

        # Regular fields should still be included
        self.assertIn("id", paths)
        self.assertIn("regular_field", paths)

    def test_flatten_schema_filters_nested_attributes_and_metadata(self) -> None:
        """Test that nested attributes[] and metadata[] fields are properly filtered."""
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

        # Nested attributes[] should be included
        self.assertIn("service.attributes[]", paths)
        # Nested attributes[].value should be included
        self.assertIn("service.attributes[].value", paths)
        # Other nested attributes sub-fields should be excluded
        self.assertNotIn("service.attributes[].id", paths)
        self.assertNotIn("service.attributes[].label", paths)

        # Nested metadata[] and its children should be excluded
        self.assertNotIn("service.metadata[]", paths)
        self.assertNotIn("service.metadata[].id", paths)
        self.assertNotIn("service.metadata[].value", paths)

        # Regular fields should still work
        self.assertIn("id", paths)
        self.assertIn("service", paths)
        self.assertIn("service.name", paths)


if __name__ == "__main__":
    unittest.main()
