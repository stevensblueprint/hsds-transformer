"""
DAG model of HSDS 3.1.2 entity relationships.
Source: https://docs.openreferral.org/en/v3.1.2/hsds/schema_reference.html#

Notes about certain entity relationships:

Service has ids that relate to Organization and Program, which causes
a cyclic dependency.
- RESOLUTION: Service is made to be a root entity (with no outgoing edges)
  and an outgoing edge to Service was made for Organization and Program.

Service Capacity has both an id for and field for Unit.
- RESOLUTION: Unit now has an outgoing edge to Service Capacity as a
  defined Unit entity must exist first.

Regarding Taxonomy Term and Taxonomy entities
- Despite the names, both can be processed independently as neither have
  fields that directly reference each other. At most Taxonomy Term has
  an id for a Taxonomy entity, but not a field that references an actual
  Taxonomy.

"""

HSDS_RELATIONS = {
    # Core
    "organization": [
        "service"
    ],

    "service": [],
    
    "location": [
        "organization"
    ],
    
    "service_at_location": [
        "service",
        "location"
    ],

    # Other
    "address": [
        "location"
    ],

    "phone": [
        "location",
        "service",
        "organization",
        "contact",
        "service_at_location"
    ],

    "schedule": [
        "service",
        "location",
        "service_at_location"
    ],

    "service_area": [
        "service",
        "service_at_location"
    ],

    "language": [
        "service",
        "location",
        "phone"
    ],

    "funding": [
        "organization",
        "service"
    ],

    "accessibility": [
        "location"
    ],

    "cost_option": [
        "service"
    ],
    
    "program": [
        "organization",
        "service"
    ],
    
    "required_document": [
        "service"
    ],
    
    "contact": [
        "organization",
        "service",
        "service_at_location",
        "location"
    ],
    
    "organization_identifier": [
        "organization"
    ],

    "unit": [
        "service_capacity"
    ],
    
    "service_capacity": [
        "service"
    ],

    "attribute": [
        "organization",
        "service",
        "location",
        "service_at_location",
        "address",
        "phone",
        "schedule",
        "service_area",
        "language",
        "funding",
        "accessibility",
        "cost_option",
        "program",
        "required_document",
        "contact",
        "organization_identifier",
        "unit",
        "url",
        "meta_table_description"
    ],
    
    "url": [
        "organization",
        "service"
    ],
    
    "metadata": [
        "organization",
        "service",
        "location",
        "service_at_location",
        "address",
        "phone",
        "schedule",
        "service_area",
        "language",
        "funding",
        "accessibility",
        "cost_option",
        "program",
        "required_document",
        "contact",
        "organization_identifier",
        "unit",
        "attribute",
        "url",
        "meta_table_description",
        "taxonomy"
    ],
    
    "meta_table_description": [],

    "taxonomy": [],
    
    "taxonomy_term": [
        "attribute"
    ]
}