import os
import json


def ingest_json_directory(directory_path: str) -> list[dict]:
    """
    Read all JSON files from a directory and return as a list of dictionaries.
    
    Args:
        directory_path: Path to directory containing JSON files
        
    Returns:
        List of dictionaries, one per JSON file
    """
    results = []
    
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                results.append(json.load(f))
    
    return results