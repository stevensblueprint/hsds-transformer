import unittest
from src.lib.collections import build_collections, searching_and_assigning

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
                        "description": "Medical center."
                    }
                ]
            )
        ]
        results = build_collections("data/iCarol") # Builds collections
        results = searching_and_assigning(results) # Links and cleans up        
        self.assertEqual(expected,results)
        
    def test2(self):
        """
        Verifies that a mapping file with no input_files_field values produces no records.
        """
        results = build_collections("data/simple_mapping")
        results = searching_and_assigning(results)
        all_objects = [obj for _, objs in results for obj in objs]
        self.assertEqual(all_objects, [])
        

    def test3(self):
        """
        Verifies that the split feature correctly splits comma-separated
        language strings into individual language objects.
        """
        results = build_collections("data/split_test")
        results = searching_and_assigning(results)
        results_dict = {name: objs for name, objs in results}

        self.assertIn("service", results_dict)

        services = results_dict["service"]
        self.assertEqual(len(services), 7)

        service_ids = [s["id"] for s in services]
        for expected_id in ["162670", "215542", "2029585", "1262081", "176054", "131293", "236966"]:
            self.assertIn(expected_id, service_ids)

        # Every service should have a singular embedded organization (not a list)
        for service in services:
            self.assertIn("organization", service)
            self.assertIsInstance(service["organization"], dict)

        # Services with a non-empty organization_name get a name field
        aurora = next(s for s in services if s["id"] == "162670")
        self.assertEqual(aurora["organization"]["name"], "AURORA COMPREHENSIVE COMMUNITY MENTAL HEALTH CENTER, INC")

        # Service with empty organization_name gets no name field
        no_name = next(s for s in services if s["id"] == "1262081")
        self.assertNotIn("name", no_name["organization"])

        # Service with no languages_spoken still produces a language entry with empty name
        aurora_langs = aurora["languages"]
        self.assertEqual(len(aurora_langs), 1)
        self.assertEqual(aurora_langs[0]["name"], "")

        # The split feature: "{English,Spanish}" -> two language objects
        trenza = next(s for s in services if s["id"] == "236966")
        lang_names = [l["name"] for l in trenza["languages"]]
        self.assertEqual(len(lang_names), 2)
        self.assertIn("English", lang_names)
        self.assertIn("Spanish", lang_names)
        
    def test4(self):
        """
        Verifies one-to-many relationship linking: locations are nested into
        their parent organizations, and field name mapping is applied correctly
        (e.g. 'address' -> 'address_1', 'state' -> 'state_province').
        """
        results = build_collections("data/logger_test")
        results = searching_and_assigning(results)
        results_dict = {name: objs for name, objs in results}

        # Organizations are present; locations have been consumed into them
        self.assertIn("organization", results_dict)
        self.assertEqual(results_dict.get("location", []), [])

        orgs = results_dict["organization"]
        self.assertEqual(len(orgs), 2)

        org_ids = [o["id"] for o in orgs]
        self.assertIn("org_001", org_ids)
        self.assertIn("org_002", org_ids)

        food_bank = next(o for o in orgs if o["id"] == "org_001")
        health_center = next(o for o in orgs if o["id"] == "org_002")

        # Organization fields
        self.assertEqual(food_bank["name"], "Food Bank of Example County")
        self.assertEqual(food_bank["description"], "Provides food assistance to families in need")

        # Food Bank has 2 locations, Health Center has 1
        self.assertIsInstance(food_bank["locations"], list)
        self.assertEqual(len(food_bank["locations"]), 2)
        self.assertEqual(len(health_center["locations"]), 1)

        # Location IDs are correctly assigned
        food_bank_loc_ids = [l["id"] for l in food_bank["locations"]]
        self.assertIn("loc_001", food_bank_loc_ids)
        self.assertIn("loc_002", food_bank_loc_ids)
        self.assertEqual(health_center["locations"][0]["id"], "loc_003")

        # Field name mapping: 'address' -> 'address_1', 'state' -> 'state_province'
        main_center = next(l for l in food_bank["locations"] if l["id"] == "loc_001")
        self.assertEqual(main_center["address_1"], "123 Main St")
        self.assertEqual(main_center["city"], "Exampleville")
        self.assertEqual(main_center["state_province"], "EX")


if __name__ == '__main__':
    unittest.main()