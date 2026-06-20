# Scoring Systems References

用途：集中存放内容约束/原子评分点相关外部评分系统资料，供 agent-eval-suite 评分细则设计参考。

## 目录

- `ifeval/`：可验证指令、checker、prompt-level / instruction-level accuracy。
- `infobench/`：复杂指令拆分、decomposed requirements、DRFR。
- `complexbench/`：约束组合、scoring question、依赖聚合。
- `complexconstraints/`：atomic criteria、Primary Intent / Extra Credit / Dodged Bullet。

## 使用

逐个目录查看 `README.md` 和原始资料；分析后把可迁移规则写入 `rubrics/scoring-templates.yaml`，不要在本目录另起项目治理规则。
