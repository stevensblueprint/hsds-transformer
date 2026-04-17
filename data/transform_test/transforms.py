"""
User-defined custom transforms for the transform_test dataset.
Passed to the transformer via: --transforms data/transform_test/transforms.py
"""


def title_case(v):
    """Capitalize the first letter of each word."""
    return v.title()


def format_phone(v):
    """Format a 10-digit string as NXX-NXX-XXXX. Expects digits only (strip runs first)."""
    return f"{v[:3]}-{v[3:6]}-{v[6:]}"


def sort_names(lst):
    """Sort a list of {"name": ...} objects alphabetically by name."""
    return sorted(lst, key=lambda x: x["name"])


transforms = {
    "title_case": title_case,
    "format_phone": format_phone,
    "sort_names": sort_names,
}

hooks = {}
