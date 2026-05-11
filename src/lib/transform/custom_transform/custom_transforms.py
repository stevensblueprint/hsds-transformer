def normalize_name(value):
    return value.title()


def clean_phone(value):
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) != 10:
        raise ValueError(f"Expected 10 digits, got {len(digits)}")
    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"


transforms = {
    "normalize_name": normalize_name,
    "clean_phone": clean_phone,
}
