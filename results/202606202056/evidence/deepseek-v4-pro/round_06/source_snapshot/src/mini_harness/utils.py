import re

def to_snake_case(name: str) -> str:
    """Convert string to snake_case."""
    # Insert underscore before each uppercase letter (except at start), then lowercase
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    # Replace non-alphanumeric characters with underscore
    s3 = re.sub(r'[^a-zA-Z0-9]', '_', s2)
    # Remove multiple underscores and leading/trailing underscores
    s4 = re.sub(r'_+', '_', s3).strip('_').lower()
    return s4
