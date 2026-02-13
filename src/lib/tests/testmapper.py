import unittest
import json
import csv
import os
from ..mapper import nested_map

class TestMapping(unittest.TestCase):
    '''Tests for transformer / nested mapping'''
    dataDict = {
        "input_filename": {
            "entity_id": "org-123",
            "entity_name": "Acme Corp",
            "entity_description": "A fictional company",
            "Phone1Number": "123-456-8910",
            "Phone2Number": "098-765-4321"
        }
    }

    mappingDict = {
        "id": {"path": "input_filename.entity_id"},
        "name": {"path": "input_filename.entity_name", "strip": ["<p>", "[", "]"]},
        "description": {"path": "input_filename.entity_description", "split": ","},
        "phones": [
            {
                "number": {
                    "path": [
                        "input_filename.Phone1Number",
                        "input_filename.Phone2Number"
                    ]
                }
            }
        ]
    }

    expected = {
        "id": "org-123",
        "name": "Acme Corp",
        "description": [
            {"description": "A fictional company"}
        ],
        "phones": [
            {"number": "123-456-8910"},
            {"number": "098-765-4321"}
        ]
    }
    def test_nested_map(self):
        self.assertEqual(nested_map(self.dataDict,self.mappingDict),self.expected)    
if __name__ == '__main__':
    unittest.main()