import re

def snake_case(s):
    # Convert camelCase or PascalCase to snake_case, and replace spaces/hyphens with underscores
    s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
    s = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()
    return re.sub(r'[\s\-]+', '_', s)
