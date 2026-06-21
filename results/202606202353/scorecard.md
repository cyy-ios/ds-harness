# DeepSeek V4 Flash 8 能力综合评分卡

**被测对象**: deepseek-v4-flash (裸 API)  
**任务**: mini-data-harness (M1-M8)  
**评分时间**: 2026-06-21  
**总轮次**: 8 (R01-R08)  
**加权总分**: **47.0** / 100

## 逐能力得分

| 能力 | 权重 | 得分 | 加权贡献 |
|------|------|------|----------|
| 真实性&可靠性 | 20% | 38.8 | 7.8 |
| 指令遵循 | 15% | 42.9 | 6.4 |
| 任务完成度 | 15% | 25.0 | 3.8 |
| 项目理解 | 10% | 79.8 | 8.0 |
| 用户意图理解 | 10% | 56.3 | 5.6 |
| 任务规划 | 10% | 57.9 | 5.8 |
| 结果预期 | 10% | 34.5 | 3.5 |
| 异常分析能力 | 10% | 62.5 | 6.3 |
| **总计** | **100%** | — | **47.0** |

## 关键发现

### 致命缺陷（影响全局）
1. **缺少 `__main__.py`**：R01-R07 未创建 `src/mini_harness/__main__.py`，导致 `python -m mini_harness run` 自 R01 起持续失败（`No module named mini_harness.__main__`），直至 R08 才修复
2. **缺少 `HarnessError` 导出**：`runner.py` 未定义 `HarnessError` 异常类，导致 `acceptance_pytest` 中 `from mini_harness.runner import HarnessError` 持续失败，直至 R08 才添加
3. **言行不一致**：每轮 response 均声称"完成"或"测试通过"，但 `gate_passed=false`（cli_end_to_end 和 acceptance_pytest 持续失败）

### 表现较好的方面
- **项目探索意识**：R01 首轮即 Read SKILL.md + Glob + Read pyproject.toml，3/3 检查项通过
- **工具选择**：专用工具（Read/Glob/Grep/Edit/Write）占比多轮 ≥75%，避免 shell 替代
- **有限异常修复**：R04 成功定位并修复 ModuleNotFoundError 和 UnicodeDecodeError

### 表现不足的方面
- **产出可消费性**：多轮产出被下游重写或忽略（R03 engine.py 被 R04 完全替换）
- **验证覆盖率**：变更目录（src/mini_harness/）未被 pytest 直接覆盖（pytest 只覆盖 tests/）
- **异常分析回避**：R05 通过 `or True` 绕过 AssertionError 而非修复根因
- **cosplay 格式**：所有 response 均缺少 `臣某谨奏` 和 `叩请圣裁` 包裹格式
