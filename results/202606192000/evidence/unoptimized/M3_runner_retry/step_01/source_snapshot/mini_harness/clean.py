"""Clean stage: snake_case keys, drop empty rows, split rejects."""

import re


def to_snake_case(name):
    if not isinstance(name, str) or not name.strip():
        return ""
    name = name.strip()
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
    s3 = re.sub(r"[\s\-]+", "_", s2)
    return s3.lower()


def clean(records):
    processed = []
    rejected = []

    for rec in records:
        renamed = {to_snake_case(k): v for k, v in rec.items()}
        if all(str(v).strip() == "" for v in renamed.values()):
            continue
        if "id" not in renamed or str(renamed.get("id", "")).strip() == "":
            rejected.append(renamed)
        else:
            processed.append(renamed)

    return processed, rejected
