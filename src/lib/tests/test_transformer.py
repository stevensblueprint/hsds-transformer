import unittest
import json
import csv
import os
from ..collections import build_collections, searching_and_assigning
from ..outputs import save_objects_to_json

class TestTransformation(unittest.TestCase):

    def test1(self):
        expected = [
            (
                "organization", 
                [
                    {
                        "id": "87138316",
                        "name": "Woda Cooper Companies - Cumberland Meadows"
                    },
                    {
                        "id": "87138319",
                        "name": "Garrett Regional Medical Center",
                        "description": "<p>Medical center.</p>"
                    }
                ]
            )
        ]
        results = build_collections("data/iCarol") # Builds collections
        results = searching_and_assigning(results) # Links and cleans up        
        self.assertEqual(expected,results)
        
    def test2(self):
        expected = """
[]
        """
        results = build_collections("data/simple_mapping") # Builds collections
        results = searching_and_assigning(results) # Links and cleans up
        output_json = json.dumps(results, indent=2, ensure_ascii=False) # Convert to json string 
        self.assertEqual(json.loads(expected),results)
        

    def test3(self):
        expected = """
[
  [
    "service",
    [
      {
        "id": "162670",
        "organization": {
          "id": "a195945f-678c-5ca4-86bc-e7812c215716",
          "name": "AURORA COMPREHENSIVE COMMUNITY MENTAL HEALTH CENTER, INC"
        },
        "languages": [
          {
            "name": ""
          }
        ]
      },
      {
        "id": "215542",
        "organization": {
          "id": "a195945f-678c-5ca4-86bc-e7812c215716",
          "name": "INNER SELF AND WISDOM, LLC"
        },
        "languages": [
          {
            "name": ""
          }
        ]
      },
      {
        "id": "2029585",
        "organization": {
          "id": "a195945f-678c-5ca4-86bc-e7812c215716",
          "name": "COLORADO COALITION FOR THE HOMELESS"
        },
        "languages": [
          {
            "name": ""
          }
        ]
      },
      {
        "id": "1262081",
        "organization": {
          "id": "a195945f-678c-5ca4-86bc-e7812c215716"
        },
        "languages": [
          {
            "name": ""
          }
        ]
      },
      {
        "id": "176054",
        "organization": {
          "id": "a195945f-678c-5ca4-86bc-e7812c215716",
          "name": "COLORADO IN-HOME COUNSELING"
        },
        "languages": [
          {
            "name": ""
          }
        ]
      },
      {
        "id": "131293",
        "organization": {
          "id": "a195945f-678c-5ca4-86bc-e7812c215716",
          "name": "BUFFALO RUN GROUP HOME, INC."
        },
        "languages": [
          {
            "name": ""
          }
        ]
      },
      {
        "id": "236966",
        "organization": {
          "id": "a195945f-678c-5ca4-86bc-e7812c215716",
          "name": "LA TRENZA COUNSELING INC."
        },
        "languages": [
          {
            "name": "English"
          },
          {
            "name": "Spanish"
          }
        ]
      }
    ]
  ]
]
"""
        results = build_collections("data/split_test") # Builds collections
        results = searching_and_assigning(results) # Links and cleans up
        output_json = json.dumps(results, indent=2, ensure_ascii=False) # Convert to json string 
        self.assertEqual(json.loads(expected),results)
        
if __name__ == '__main__':
    unittest.main()