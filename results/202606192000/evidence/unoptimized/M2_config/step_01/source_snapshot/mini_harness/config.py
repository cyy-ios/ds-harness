"""Config loader: JSON natively, minimal YAML via standard library."""

import json
import re
from pathlib import Path


def load_config(config_path, repo_root):
    """Load config from a JSON or YAML file. Returns dict."""
    path = Path(config_path)
    if not path.is_absolute():
        path = Path(repo_root) / path
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    ext = path.suffix.lower()
    if ext == ".json":
        return _load_json(str(path))
    if ext in (".yaml", ".yml"):
        return _load_yaml(str(path))
    raise ValueError(f"Unsupported config format: {ext}")


def find_default_config(repo_root):
    """Look for a default config file in repo root. Returns path or None."""
    candidates = [
        "mini_harness.json",
        "mini_harness.yaml",
        "mini_harness.yml",
        "config.json",
        "config.yaml",
        "config.yml",
    ]
    root = Path(repo_root)
    for name in candidates:
        candidate = root / name
        if candidate.exists():
            return str(candidate)
    return None


def _load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


# --- minimal YAML parser (no third-party deps) ---

def _load_yaml(path):
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    return _parse_yaml(text)


def _parse_yaml(text):
    lines = [_strip_comment(line) for line in text.splitlines()]
    lines = [ln for ln in lines if ln.strip() != ""]
    if not lines:
        return {}
    root, _ = _parse_yaml_dict(lines, 0, _get_indent(lines[0]))
    return root


def _strip_comment(line):
    in_sq = False
    in_dq = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_dq:
            in_sq = not in_sq
        elif ch == '"' and not in_sq:
            in_dq = not in_dq
        elif ch == "#" and not in_sq and not in_dq:
            return line[:i].rstrip()
    return line


def _get_indent(line):
    return len(line) - len(line.lstrip(" "))


def _parse_yaml_value(lines, idx):
    """Parse one or more lines starting at idx. Returns (value, next_idx)."""
    if idx >= len(lines):
        return None, idx

    line = lines[idx]
    stripped = line.strip()
    indent = _get_indent(line)

    if stripped.startswith("- "):
        return _parse_yaml_list(lines, idx, indent)
    if ":" in stripped and not stripped.startswith(("{", "[", "'", '"')):
        key, _, val = stripped.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "":
            return _parse_yaml_dict(lines, idx, indent)
        else:
            return {key: _scalar(val)}, idx + 1
    return _scalar(stripped), idx + 1


def _parse_yaml_dict(lines, idx, base_indent):
    result = {}
    i = idx
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        indent = _get_indent(line)
        if indent < base_indent and stripped:
            break
        if indent == base_indent and stripped:
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                if val == "":
                    i += 1
                    if i < len(lines) and _get_indent(lines[i]) > base_indent:
                        result[key], i = _parse_yaml_value(lines, i)
                        continue
                    else:
                        result[key] = None
                        continue
                else:
                    result[key] = _scalar(val)
        i += 1
    return result, i


def _parse_yaml_list(lines, idx, base_indent):
    result = []
    i = idx
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        indent = _get_indent(line)
        if indent < base_indent and stripped:
            break
        if indent == base_indent and stripped.startswith("- "):
            item_text = stripped[2:].strip()
            if item_text == "":
                i += 1
            elif ":" in item_text:
                key, _, val = item_text.partition(":")
                val = val.strip()
                if val == "":
                    i += 1
                    if i < len(lines) and _get_indent(lines[i]) > base_indent:
                        nested, i = _parse_yaml_value(lines, i - 1)
                        result.append(nested)
                        continue
                    else:
                        result.append({key: None})
                        continue
                else:
                    result.append({key: _scalar(val)})
            else:
                result.append(_scalar(item_text))
        i += 1
    return result, i


def _scalar(s):
    """Parse a YAML scalar: int, float, bool, null, or string."""
    s = s.strip()
    if s == "" or s.lower() == "null" or s == "~":
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if re.match(r"^-?\d+$", s):
        return int(s)
    if re.match(r"^-?\d+\.\d+$", s):
        return float(s)
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    return s
