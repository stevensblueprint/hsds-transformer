"""
DAG model of HSDS 3.1.2 entity relationships.
Source: https://docs.openreferral.org/en/v3.1.2/hsds/schema_reference.html#
"""

# TODO: Resolve cycles:
# organization <=> service <=> program
# unit <=> service_capacity
# taxonomy <=> taxonomy_term

HSDS_RELATIONS = {
    # Core
    "organization": [
        "service"
    ],

    "service": [
        "organization",
        "program",
    ],
    
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
        "organization"
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

    "unit": [],
    
    "service_capacity": [
        "service"
        "unit"
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