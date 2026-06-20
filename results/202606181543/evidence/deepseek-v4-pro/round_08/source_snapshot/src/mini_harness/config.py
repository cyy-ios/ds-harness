import json
import os

def parse_yaml(content):
    """Very basic YAML parser handling strings, numbers, lists, and maps."""
    lines = content.strip().split('\n')
    result = _parse_yaml_lines(lines, indent_level=0)
    # _parse_yaml_lines may return None for empty document
    if result is None:
        return {}
    return result

def _parse_yaml_lines(lines, indent_level=0):
    """Recursive parser."""
    result = None
    current_indent = indent_level * 2
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        # measure indentation
        stripped = line.lstrip(' ')
        indent = len(line) - len(stripped)
        if indent < current_indent:
            break  # back to parent level
        if stripped.startswith('#'):
            i += 1
            continue
        # check if it's a list item
        if stripped.startswith('- '):
            if result is None:
                result = []
            value_part = stripped[2:].strip()
            if ':' in value_part and not value_part.startswith(('"', "'")):
                # inline mapping
                key, val = value_part.split(':', 1)
                item = {key.strip(): val.strip()}
            else:
                item = _parse_scalar(value_part)
            result.append(item)
            i += 1
        elif ':' in stripped:
            if result is None:
                result = {}
            key, val = stripped.split(':', 1)
            key = key.strip()
            val = val.strip()
            if val == '':
                # nested mapping or list
                nested_lines = []
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if not next_line.strip():
                        i += 1
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip(' '))
                    if next_indent <= indent:
                        break
                    nested_lines.append(next_line)
                    i += 1
                nested_val = _parse_yaml_lines(nested_lines, indent_level + 1)
                result[key] = nested_val
                continue  # i already advanced
            else:
                # scalar value
                result[key] = _parse_scalar(val)
                i += 1
        else:
            # plain scalar (might be top-level list without dash?)
            if result is None:
                # could be multi-line scalar? fallback
                result = stripped
            i += 1
    return result

def _parse_scalar(val):
    """Convert string to Python scalar."""
    val = val.strip()
    # remove surrounding quotes
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    # try numbers
    if val.lower() == 'true':
        return True
    if val.lower() == 'false':
        return False
    if val.lower() == 'null':
        return None
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val

def load_config(file_path):
    """Load config from JSON or YAML file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.json':
        return json.loads(content)
    elif ext in ('.yaml', '.yml'):
        return parse_yaml(content)
    else:
        raise ValueError(f"Unsupported config format: {ext}. Use .json or .yaml")
