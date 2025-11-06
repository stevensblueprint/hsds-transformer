def is_valid_id(id_value) -> bool:
    """
    Check if an ID value is valid (non-empty, non-null, meaningful).
    """
    if id_value is None:
        return False
    
    id_str = str(id_value).strip()
    
    # Check for empty string or common "empty" values
    if not id_str or id_str.lower() in ["null", "none", "n/a", "na"]:
        return False
    
    return True


def identify_parent_relationships(obj_dict: dict) -> list[tuple[str, str]]:
    """
    Given an HSDS object dictionary, identify parent relationships.
    
    Looks for all keys ending with '_id' (except the object's own 'id' field),
    validates the ID values, and returns a list of parent relationships.
    """
    # Initialize empty list for relationships
    relationships = []
    
    for key, value in obj_dict.items():
        # Skip the object's own id field and look for parent_id fields
        if key.endswith('_id') and key != 'id':
            # Validate the ID value
            if is_valid_id(value):
                # Remove the '_id' suffix to get the parent type
                parent_type = key[:-3]
                # Append the parent relationship to the list
                relationships.append((parent_type, str(value)))
    
    return relationships
