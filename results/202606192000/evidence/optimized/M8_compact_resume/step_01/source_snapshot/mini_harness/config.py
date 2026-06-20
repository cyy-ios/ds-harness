"""Configuration loader: JSON and minimal YAML support (stdlib only)."""
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG_NAMES = ("mini_harness.json", "mini_harness.yaml", "mini_harness.yml")


def load_config(
    repo_root: Path,
    explicit_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Load config from explicit path, or auto-discover in repo_root.

    Auto-discovery order: mini_harness.json > mini_harness.yaml > mini_harness.yml
    Returns empty dict if no config found.
    """
    if explicit_path is not None:
        if not explicit_path.exists():
            raise FileNotFoundError(f"Config file not found: {explicit_path}")
        return _parse_file(explicit_path)

    for name in DEFAULT_CONFIG_NAMES:
        candidate = repo_root / name
        if candidate.exists():
            return _parse_file(candidate)

    return {}


def _parse_file(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    with open(path, "r", encoding="utf-8-sig") as f:
        raw = f.read()
    if suffix == ".json":
        return json.loads(raw)
    if suffix in (".yaml", ".yml"):
        return _parse_yaml(raw)
    raise ValueError(f"Unsupported config format: {suffix}")


# ---------------------------------------------------------------------------
# Minimal YAML parser (stdlib only)
# Supports: scalars, nested mappings, sequences, comments, quoted strings
# ---------------------------------------------------------------------------

def _parse_yaml(text: str) -> Dict[str, Any]:
    lines = _yaml_lines(text)
    root, _ = _parse_node(lines, 0)
    if not isinstance(root, dict):
        raise ValueError("YAML root must be a mapping")
    return root


def _yaml_lines(text: str) -> list[tuple[int, str]]:
    """Return list of (indent, content) for non-empty, non-comment lines."""
    out: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = raw.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        out.append((indent, stripped))
    return out


def _parse_node(
    lines: list[tuple[int, str]], pos: int,
) -> tuple[Any, int]:
    """Parse one YAML node starting at pos; return (value, next_pos)."""
    if pos >= len(lines):
        return None, pos

    indent, content = lines[pos]

    # sequence entry
    if re.match(r"^-\s+", content):
        return _parse_sequence(lines, pos, indent)

    # mapping
    if re.match(r"^[^:]+:", content):
        return _parse_mapping(lines, pos, indent)

    return content, pos + 1


def _parse_sequence(
    lines: list[tuple[int, str]], pos: int, base_indent: int,
) -> tuple[list[Any], int]:
    result: list[Any] = []
    i = pos
    while i < len(lines):
        ci, content = lines[i]
        if ci != base_indent:
            break
        body = content[base_indent:]
        m = re.match(r"^-\s+(.*)", body)
        if not m:
            break
        rest = m.group(1).strip()
        if rest == "":
            # block sequence with nested content on next line(s)
            i += 1
            if i < len(lines) and lines[i][0] > base_indent:
                child: dict[str, Any] = {}
                i = _parse_nested_mapping(lines, i, base_indent, child)
                result.append(child)
            else:
                result.append(None)
        elif re.match(r"^[^:]+:", rest):
            # inline mapping in sequence: "- key: value"
            mk = re.match(r"^([^:]+?):\s*(.*)", rest)
            if mk:
                child = {mk.group(1).strip(): _coerce_scalar(mk.group(2).strip())}
                result.append(child)
            i += 1
        else:
            result.append(_coerce_scalar(rest))
            i += 1
    return result, i


def _parse_nested_mapping(
    lines: list[tuple[int, str]], pos: int, parent_indent: int, target: dict,
) -> int:
    """Parse lines at deeper indent into target dict; return next pos."""
    i = pos
    while i < len(lines):
        ci, content = lines[i]
        if ci <= parent_indent:
            break
        key, value, consumed = _parse_one_kv(lines, i, ci)
        target[key] = value
        i += consumed
    return i


def _parse_mapping(
    lines: list[tuple[int, str]], pos: int, base_indent: int,
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    i = pos
    while i < len(lines):
        ci = lines[i][0]
        if ci != base_indent:
            break
        key, value, consumed = _parse_one_kv(lines, i, base_indent)
        result[key] = value
        i += consumed
    return result, i


def _parse_one_kv(
    lines: list[tuple[int, str]], pos: int, base_indent: int,
) -> tuple[str, Any, int]:
    """Parse a single key: value at pos; return (key, value, lines_consumed)."""
    ci, content = lines[pos]
    m = re.match(r"^([^:]+?):(?:\s+(.*))?$", content)
    if not m:
        return content, None, 1
    key = m.group(1).strip()
    rest = m.group(2)

    if rest is None or rest == "":
        # value on next line(s) at deeper indent
        if pos + 1 < len(lines) and lines[pos + 1][0] > base_indent:
            next_content = lines[pos + 1][1].lstrip()
            if next_content.startswith("- "):
                # list
                seq, next_pos = _parse_sequence(lines, pos + 1, lines[pos + 1][0])
                return key, seq, next_pos - pos
            else:
                # nested mapping
                child: dict[str, Any] = {}
                next_pos = _parse_nested_mapping(lines, pos + 1, base_indent, child)
                return key, child, next_pos - pos
        return key, None, 1

    rest = rest.strip()
    if rest == "[]":
        # empty list — check for block items
        if pos + 1 < len(lines) and lines[pos + 1][0] > base_indent:
            seq, next_pos = _parse_sequence(lines, pos + 1, lines[pos + 1][0])
            return key, seq, next_pos - pos
        return key, [], 1

    return key, _coerce_scalar(rest), 1


def _coerce_scalar(raw: str) -> Any:
    if raw == "null" or raw == "~":
        return None
    if raw == "true":
        return True
    if raw == "false":
        return False
    if (raw.startswith('"') and raw.endswith('"')) or \
       (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw
