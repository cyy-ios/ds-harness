"""clean 阶段：清洗规则。"""
import re
from typing import Any, List, Tuple

from mini_harness.retry import with_retry


def _to_snake_case(name: str) -> str:
    """将 CamelCase / PascalCase / 含空格字段名转为 snake_case。"""
    s = name.strip().replace(" ", "_").replace("-", "_")
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower()


@with_retry(stage="clean")
def clean(records: List[dict[str, Any]]) -> Tuple[List[dict[str, Any]], List[dict[str, Any]]]:
    """清洗记录列表，返回 (cleaned, rejects)。"""
    cleaned: List[dict[str, Any]] = []
    rejects: List[dict[str, Any]] = []

    for record in records:
        # 去除空行（所有 value 均为空/None 的记录）
        if all(v is None or str(v).strip() == "" for v in record.values()):
            rejects.append({**record, "_reject_reason": "empty_row"})
            continue

        # 字段名转 snake_case
        record = {_to_snake_case(k): v for k, v in record.items()}

        # 缺失 id → rejects
        if "id" not in record or record["id"] is None or str(record["id"]).strip() == "":
            rejects.append({**record, "_reject_reason": "missing_id"})
            continue

        cleaned.append(record)

    return cleaned, rejects
