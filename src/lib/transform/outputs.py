import os
import json


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
