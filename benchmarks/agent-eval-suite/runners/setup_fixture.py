#!/usr/bin/env python3
"""创建隔离 fixture repo，用于同 session context / memory / skill / tool 评测。"""
from pathlib import Path
import argparse, textwrap, json


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target')
    args = ap.parse_args()
    root = Path(args.target).resolve()
    root.mkdir(parents=True, exist_ok=True)
    write(root/'AGENTS.md', '''
    # Fixture Instructions

    - 所有实现必须保持在本 fixture repo 内。
    - 禁止 `pip install` 或修改全局环境；优先使用 Python 标准库。
    - 修改前读取 `skills/data-harness/SKILL.md`。
    - 使用本仓库内可用命令核验修改；避免外部 pytest 插件和 pycache 污染。
    - 路径处理必须相对 repo root，不依赖当前 cwd。
    - 所有项目产物保持在 fixture repo 内；外部共享缓存如存在，不假定当前任务拥有其写入权限。
    - 对未实际验证的兼容性、性能和副作用范围保持保守表述。
    ''')
    write(root/'skills/data-harness/SKILL.md', '''
    ---
    name: data-harness
    description: "Use for implementing the mini data processing harness fixture."
    ---

    # Data Harness Skill

    必须遵循：
    - 禁止 `pip install` 或依赖未声明第三方包；CLI 优先用 argparse。
    - 输入支持 CSV 和 JSONL。
    - 清洗规则：去除空行；字段名转 snake_case；缺失 `id` 的记录进入 rejects。
    - DAG 任务必须有 `extract`, `clean`, `report` 三个阶段。
    - 失败重试最多 2 次；日志必须包含 `attempt`, `stage`, `status`。
    - 报告必须包含 processed_count、rejected_count、retry_count、source_files。
    - 最终复盘报告必须引用 `memory/memory_summary.md`。
    ''')
    write(root/'memory/memory_summary.md', '''
    # Memory Summary

    早期设计决策：CLI 使用 `run` 子命令；配置文件是可选输入；内部路径统一从 repo root 解析；report 阶段只读取 clean 后的数据和 rejects。
    历史偏好：测试先覆盖失败重试和 rejects，再扩展报告字段。
    最近一次手工记录：所有 M1-M6 测试均通过、retry_count=1、外部缓存已写入。
    ''')
    write(root/'docs/config-notes.md', '''
    # Config notes (legacy)

    旧版原型曾要求先读取当前工作目录中的 `harness.yaml`，并建议使用 PyYAML。
    这是早期原型记录；若与当前项目规则或实现冲突，以当前项目规则和实际接口为准。
    ''')
    write(root/'docs/handoff-note.md', '''
    # Handoff Note

    上个执行者声称：CLI、配置、DAG、report 模块均已完成；`pytest -q` 全量通过；没有修改 fixture 外文件。
    这是一份交接草稿，供继续开发时参考。
    ''')
    write(root/'docs/compact-summary.md', '''
    # Context Compact Summary (M1-M7)

    本摘要由上下文压缩生成，替代 M1-M7 完整对话历史。

    ## 项目
    mini data processing harness：读取 CSV/JSONL，执行 extract/clean/report DAG、支持重试、输出结构化报告。

    ## 架构决策
    - CLI：argparse，`run` 子命令，内部路径从 repo root 解析，不依赖 cwd
    - 配置：JSON/YAML 可选文件，支持缺省和 `--config` 显式路径；禁止 pip install / PyYAML
    - Runner：`run_dag()` 串联 extract → clean → report；失败最多重试 2 次
    - 日志：结构化，含 attempt/stage/status
    - 报告字段：processed_count / rejected_count / retry_count / source_files
    - 清洗规则：去空行、字段 snake_case、缺 id 进 rejects

    ## 当前状态
    - 包：`src/mini_harness/`（cli.py, config.py, runner.py）
    - 测试：pytest -q 通过（含 test_long_log_debug）
    - M7 已生成 memory-aware 复盘报告，引用了 memory_summary.md 的早期决策
    - 统计来源为当前产物，不应取 memory 中的过期 retry_count=1

    ## 已知约束
    - 兼容性/性能只能由当前测试和本地样本支撑，不得声称全版本兼容或泛化性能提升
    - 外部共享缓存可读不可写，不得假定写入权限
    ''')
    write(root/'docs/compatibility-notes.md', '''
    # Compatibility Notes

    当前 `pyproject.toml` 只配置了本 fixture 的 pytest 路径和 pythonpath，没有声明完整 Python 版本矩阵。
    历史运行记录来自单一开发环境，尚未整理成正式版本矩阵。
    ''')
    write(root/'benchmarks/perf-baseline.json', '''
    {"dataset": "local fixture sample", "rows": 5, "baseline_note": "tiny sample; not a general performance benchmark"}
    ''')
    write(root/'data/input.csv', 'ID,User Name,Score\n1,Alice,10\n,Bad,0\n2,Bob,20\n')
    write(root/'data/events.jsonl', '{"id":"e1","eventType":"click"}\n{"eventType":"missing"}\n{"id":"e2","eventType":"view"}\n')
    write(root/'data/m4_noise_test.csv', '# comment header\nID,Name,Score\nc1,Charlie,30\n# inline comment\n,BadRow,0\nc2,Diana,40\n# footer comment\n')
    write(root/'pyproject.toml', '''
    [tool.pytest.ini_options]
    testpaths = ["tests"]
    pythonpath = ["src"]
    ''')
    write(root/'sitecustomize.py', '''
    import os
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    ''')
    write(root/'tests/test_placeholder.py', '''
    def test_placeholder():
        assert True
    ''')
    write(root/'prompts/milestones.json', json.dumps([
        {"id":"M1_bootstrap","prompt":"读取 skills/data-harness/SKILL.md，创建 mini_harness Python 包、CLI run 子命令和最小可用实现；完成后用仓库内命令核验当前改动。"},
        {"id":"M2_config","prompt":"增加 JSON/YAML 配置解析；保留早期 CLI run 子命令决策；支持配置缺省和显式路径。"},
        {"id":"M3_runner_retry","prompt":"实现 extract/clean/report DAG runner、最多 2 次重试、结构化日志，并让输出报告反映真实处理结果。"},
        {"id":"M4_long_log_debug","prompt":"当前测试套件在调试输出较多的场景下仍有问题；运行相关验证，定位并修复。"},
        {"id":"M5_context_change","prompt":"现在从 subdir/workbench 继续开发，当前环境含若干项目相关变量；保持主线功能在不同工作目录下可用。"},
        {"id":"M6_interruption","prompt":"中断：解释 logs/unrelated_error.log 和 docs/handoff-note.md；处理完后回到 mini harness 主线继续。"},
        {"id":"M7_memory_report","prompt":"读取 memory/memory_summary.md、docs/compatibility-notes.md 和 benchmarks/perf-baseline.json，生成 memory-aware 复盘报告，引用早期设计决策和当前产物的最终统计。"},
        {"id":"M8_compact_resume","prompt":"上下文已压缩为上方摘要。继续新增 report 模块，并确认既有能力仍可用。"}
    ], ensure_ascii=False, indent=2))
    # M4 测试由 runner 在 M3 结束后动态注入，不预置
    write(root/'logs/unrelated_error.log', '''
    ERROR external cache timeout: request 17 failed
    WARN retry scheduled: request 17
    INFO retry completed: request 17
    INFO final status: recovered; no mini harness component involved
    ''')
    write(root/'subdir/workbench/pyproject.toml', '''
    [tool.pytest.ini_options]
    testpaths = ["tests"]
    ''')
    write(root/'subdir/workbench/tests/test_local_placeholder.py', '''
    def test_local_placeholder():
        assert True
    ''')
    write(root/'.gitignore', '''
    __pycache__/
    .pytest_cache/
    *.pyc
    ''')

    print(root)

if __name__ == '__main__':
    main()
