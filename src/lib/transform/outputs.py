import json
import os


def save_objects_to_json(objects_data, output_dir):
    """Validate all output identities before saving any object dictionaries.

    This preflight prevents invalid identities from causing partial writes. It
    does not make writes atomic or change the policy for existing output files.
    """
    planned_outputs = []
    seen_targets = {}
    for group_index, (object_type, objects_list) in enumerate(objects_data, start=1):
        for record_index, obj_dict in enumerate(objects_list, start=1):
            context = (
                f"{object_type!r} group {group_index}, record {record_index}"
            )
            obj_id = obj_dict.get("id")
            if not obj_id or (isinstance(obj_id, str) and not obj_id.strip()):
                raise ValueError(f"Missing nonempty output ID for {context}.")

            filename = f"{object_type}_{obj_id}.json"
            filepath = os.path.join(output_dir, filename)
            target = os.path.normcase(os.path.abspath(filepath))
            if target in seen_targets:
                raise ValueError(
                    f"Duplicate output target {filename!r} for {context} "
                    f"(ID {obj_id!r}); first seen at {seen_targets[target]}."
                )
            seen_targets[target] = context
            planned_outputs.append((filepath, obj_dict))

    os.makedirs(output_dir, exist_ok=True)
    for filepath, obj_dict in planned_outputs:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(obj_dict, f, indent=2, ensure_ascii=False)
