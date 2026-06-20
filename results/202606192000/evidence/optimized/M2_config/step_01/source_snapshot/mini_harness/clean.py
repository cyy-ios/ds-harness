"""clean stage: cleaning rules."""
import re
from typing import Any, List, Tuple

from mini_harness.retry import with_retry


def _to_snake_case(name: str) -> str:
    """Convert CamelCase / PascalCase / spaced field names to snake_case."""
    s = name.strip().replace(" ", "_").replace("-", "_")
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower()


@with_retry(stage="clean")
def clean(
    records: List[dict[str, Any]], **kwargs: Any,
) -> Tuple[List[dict[str, Any]], List[dict[str, Any]]]:
    """Clean record list, return (cleaned, rejects)."""
    cleaned: List[dict[str, Any]] = []
    rejects: List[dict[str, Any]] = []

    for record in records:
        # drop empty rows
        if all(v is None or str(v).strip() == "" for v in record.values()):
            rejects.append({**record, "_reject_reason": "empty_row"})
            continue

        # field names to snake_case
        record = {_to_snake_case(k): v for k, v in record.items()}

        # missing id -> rejects
        if "id" not in record or record["id"] is None or str(record["id"]).strip() == "":
            rejects.append({**record, "_reject_reason": "missing_id"})
            continue

        cleaned.append(record)

    return cleaned, rejects
