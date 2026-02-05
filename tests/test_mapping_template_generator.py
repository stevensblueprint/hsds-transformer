from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.lib.mapping_template import flatten_schema, write_mapping_template_csv

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


if __name__ == "__main__":
    unittest.main()
