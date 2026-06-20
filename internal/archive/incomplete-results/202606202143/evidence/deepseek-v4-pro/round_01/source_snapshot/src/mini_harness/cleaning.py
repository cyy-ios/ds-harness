import re

def to_snake_case(name: str) -> str:
    """Convert a string to snake_case."""
    name = re.sub(r'[\s\-]+', '_', name)
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    return name.lower().strip('_')

def clean_record(record: dict) -> dict:
    """Clean a single record: convert keys to snake_case, strip values."""
    cleaned = {}
    for key, value in record.items():
        new_key = to_snake_case(key)
        cleaned[new_key] = value.strip() if isinstance(value, str) else value
    return cleaned

def has_id(record: dict) -> bool:
    """Check if record has 'id' field."""
    # After snake_case conversion, the key should be 'id'
    return 'id' in record and record['id'] is not None and str(record['id']).strip() != ''

def clean_records(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Clean a list of records: remove empty rows, convert keys, reject missing id.
    Returns (processed, rejected).
    """
    processed = []
    rejected = []
    for record in records:
        # Skip completely empty records (all values empty)
        if all(not v or not str(v).strip() for v in record.values()):
            continue
        cleaned = clean_record(record)
        if not has_id(cleaned):
            rejected.append(cleaned)
        else:
            processed.append(cleaned)
    return processed, rejected
