"""mini_harness — 最小数据处理流水线夹具。

DAG 阶段：extract → clean → report
支持 CSV / JSONL 输入，失败重试最多 2 次。
"""

from mini_harness.cli import main as cli_main

__all__ = ["cli_main"]
