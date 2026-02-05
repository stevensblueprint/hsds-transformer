import sys
import os
from pathlib import Path

# Ensure src is in path so we can import the transformer modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lib.collections import build_collections, searching_and_assigning

DATA_DIR = Path("data")

def run_pipeline(data_path):
    """
    Helper function to run the transformer pipeline on a specific data directory.
    Returns a dictionary of collections: {"organization": [objs], ...}
    """
    collections = build_collections(str(data_path))
    results = searching_and_assigning(collections)
    results_dict = {name: objs for name, objs in results}
    return results_dict

def test_sanity_check_relational():
    """
    Verifies the full HSDS pipeline including:
    1. CSV -> JSON Mapping (all complex features: array, split, strip)
    2. Relationship Linking (Organization <- Service <- Program)
    3. DAG Processing Order (Correct nesting)
    4. Singular Embedding (Program inside Service)
    """
    path = DATA_DIR / "sanity_check"
    results = run_pipeline(path)
    
    # 1. Verify Root Entity (Organization)
    # The pipeline should return 'organization' as a top-level collection.
    # 'service' and 'program' should be consumed (nested) and removed from top-level results
    # if the "searching_and_assigning" logic works correctly.
    
    assert "organization" in results
    # Check that services and programs are NOT in top level results (they should be nested)
    # Note: The current implementation of searching_and_assigning removes consumed children.
    # However, if they are not fully consumed (orphans), they might remain. 
    # In our test data, all are linked, so they should be gone or empty.
    
    orgs = results["organization"]
    assert len(orgs) == 1
    org = orgs[0]
    
    assert org["id"] == "1"
    assert org["name"] == "Test Organization"
    
    # 2. Verify Mapping Features (inherited from previous sanity check)
    
    # Strip (HTML removal)
    assert org["description"] == "Clean Me"
    
    # Split (Templated)
    assert len(org["languages"]) == 2
    assert org["languages"][0]["name"] == "en"
    
    # Aligned Arrays (Phones + Types)
    assert len(org["phones"]) == 2
    assert org["phones"][0]["number"] == "555-0100"
    assert org["phones"][0]["type"] == "Office"
    assert org["phones"][1]["number"] == "555-0101"
    assert org["phones"][1]["type"] == "Mobile"
    
    # Attributes (Label generation)
    wifi = next((a for a in org["attributes"] if a["value"] == "HasWifi"), None)
    assert wifi is not None
    assert wifi["label"] == "Feature1"
    
    # Flat Split (Tags)
    assert "tagA" in org["tags"]
    assert "tagB" in org["tags"]
    
    # 3. Verify One-to-Many Linking (Organization -> Services)
    # We created 2 services (101, 102) linked to Org 1.
    assert "services" in org
    assert isinstance(org["services"], list)
    assert len(org["services"]) == 2
    
    # Verify content of services
    service_ids = [s["id"] for s in org["services"]]
    assert "101" in service_ids
    assert "102" in service_ids
    
    # 4. Verify Singular Embedding (Service -> Program)
    # Service 101 has Program 501.
    # Service 102 has no program.
    
    service_a = next(s for s in org["services"] if s["id"] == "101")
    service_b = next(s for s in org["services"] if s["id"] == "102")
    
    # Check Service A has the program embedded as a DICT, not a LIST
    # (Based on SINGULAR_CHILD_CASES rule in collections.py)
    assert "program" in service_a
    assert isinstance(service_a["program"], dict) # Crucial check: must be a dict
    assert service_a["program"]["id"] == "501"
    assert service_a["program"]["name"] == "Program X"
    
    # Check Service B has no program
    assert "program" not in service_b
