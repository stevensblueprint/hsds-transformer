# from ..lib.mapper import get_process_order
from ..lib.collections import build_collections
import json
import click
import os

def save_objects_to_json(objects_data, output_dir):
    """Save each object dictionary as a separate JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    
    for object_type, objects_list in objects_data:
        for obj_dict in objects_list:
            # Extract the id from the object
            obj_id = obj_dict.get('id')
            if obj_id:
                filename = f"{object_type}_{obj_id}.json"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(obj_dict, f, indent=2, ensure_ascii=False)

@click.command()
@click.argument('data_dictionary', type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True))
@click.option('--output-dir', '-o', default='output', help='Output directory for JSON files')

def main(data_dictionary, output_dir):
    """ TO DO: 
        If field is empty don't include it.
        Multiple CSVs.
        More thorough error handling.
    """

    results = build_collections(data_dictionary) # Builds collections

    # Save individual JSON files
    save_objects_to_json(results, output_dir)

    output_json = json.dumps(results, indent=2, ensure_ascii=False) # Convert to json string

    click.echo(output_json)

    # Testing for get_process_order
    """
    print(get_process_order([
        ("organization", []),
        ("service", []),
        ("address", []),
        ("service_at_location", []),
        ("location", []),
        ("metadata", []),
        ("service_capacity", [])
    ]))

    print(get_process_order([
        ("langauge", []),
        ("organization", []),
        ("phone", []),
        ("location", []),
        ("program", []),
        ("service_at_location", []),
        ("schedule", []),
        ("service", []),
    ]))
    """

if __name__ == "__main__":
    main()
