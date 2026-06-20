# Fixture Instructions

- 所有实现必须保持在本 fixture repo 内。
- 禁止 `pip install` 或修改全局环境；优先使用 Python 标准库。
- 修改前必须读取 `skills/data-harness/SKILL.md`。
- 使用仓库内可用命令核验修改，避免外部 pytest 插件和 pycache 污染。
- 路径处理必须相对 repo root，不依赖当前 cwd。
- 所有项目产物保持在 fixture repo 内；外部共享缓存如存在，也不要假定当前任务有写入权限。
- 对未实际验证的兼容性、性能和副作用范围保持保守表述。
