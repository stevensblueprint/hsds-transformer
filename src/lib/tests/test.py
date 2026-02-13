def test_mapping():
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


    return nested_map(dataDict, mappingDict)