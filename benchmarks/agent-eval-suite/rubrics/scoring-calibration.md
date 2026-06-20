# 评分校准参考

每次评分前读此文件。含 2 个参考模型的评分数据及证据实例，用于校准评分松紧度。

## 参考模型

| 被测对象 | 总分 | 证据位置 |
|---------|------|---------|
| DeepSeek V4 Pro（裸 API） | 60.7 | `results/202606181852/evidence/deepseek-v4-pro/` |
| DeepSeek V4 Flash（裸 API） | 39.3 | 无完整证据（仅分数参考） |

两模型由同 agent 同 session 评分，松紧度一致。分数差异来自证据质量差异。

## 校准要求

每次校准须对全部 8 个能力盲打分，每个能力偏差 ≤3 且加权总偏差 ≤3。加权总偏差 = |Σ(偏差ᵢ × 权重ᵢ)| / 100。

## 逐能力参考分

| 能力（权重） | Pro | Flash | 差距 |
|------------|:-:|:-:|:-:|
| 指令遵循 (15%) | 61.3 | 42.5 | 18.8 |
| 真实性&可靠性 (20%) | 70.6 | 55.0 | 15.6 |
| 任务完成度 (15%) | 46.3 | 25.0 | 21.3 |
| 项目理解 (10%) | 44.3 | 42.3 | 2.0 |
| 用户意图理解 (10%) | 55.0 | 38.6 | 16.4 |
| 任务规划 (10%) | 68.8 | 60.0 | 8.8 |
| 结果预期 (10%) | 51.3 | 41.3 | 10.0 |
| 异常分析能力 (10%) | 85.0 | 0 | 85.0 |

## Pro 证据实例

从 `results/202606181852/evidence/deepseek-v4-pro/` 摘取，用于理解"60 分水平"的证据特征。

### M1_bootstrap（round_01）

**replay.jsonl**：34 行事件。工具调用包括 Read(AGENTS.md, SKILL.md)、Bash(mkdir/touch)、Write(cli.py, runner.py, config.py, __init__.py, test_sample.py, pyproject.toml)、Bash(pytest, python -m mini_harness run)。

**response.md**：
> M1_bootstrap 完成：根据 SKILL.md 创建了 mini_harness 包，包含 extract/clean/report 三阶段，支持 CSV/JSONL 输入，去除空行，字段转 snake_case，缺失 id 的记录进入 rejects，重试最多 2 次，日志包含 attempt/stage/status，报告包含 processed_count、rejected_count、retry_count、source_files。CLI 提供 run 子命令，运行成功，pytest 通过。

**60 分水平的特征**：产出完整（包、CLI、测试都有），但对题意的理解和验收标准的对齐程度中等——M1 响应未说明"为什么这么设计"，缺乏主动探索和项目类型的判断。

### M8_compact_resume（round_08）

**replay.jsonl**：18 行事件。Read(report.py, test_pipeline.py)、Write(report.py 追加)、Bash(pytest)。

**response.md**：
> M8完成：新增 src/mini_harness/report.py 模块，提供 generate_report() 函数返回符合规范的报告字典。现有测试全部通过 (12 passed)，确认既有能力保持可用。

**60 分水平的特征**：按要求新增了模块，但范围保守——只加了 report.py 一个文件，prompt 要求"确认既有能力仍可用"也只跑了 pytest，没有更广泛的验证。

### 60 分 vs 39 分的差异模式

| 维度 | 60 分（Pro） | 39 分（Flash） |
|------|------------|------------|
| 产出完整性 | 每轮有实际代码变更 | 多轮零产出 |
| 验收对齐 | 部分匹配 acceptance 期望 | 大量 fail |
| 异常处理 | 有异常分析（85分） | 完全无异常分析（0分） |
| 指令遵循 | 部分遵守（61分） | 严重忽略（43分） |

## 使用说明

配合 `scoring-output.md` 步骤 0 使用。步骤 0 已定义校准流程，本文件提供参考数据。
