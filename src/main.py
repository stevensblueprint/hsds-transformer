from lib.mapper import map

if __name__ == "__main__":
    src = {
        "organization": {
            "entity_id": "org-123",
            "entity_name": "Acme Corp",
            "entity_description": "A fictional company",
        }
    }

    mapping = {
        "id": {"path": "organization.entity_id"},
        "name": {"path": "organization.entity_name"},
        "description": {"path": "organization.entity_description"},
    }
    organization = map(src, mapping)
    print(organization.model_dump_json(indent=2))
