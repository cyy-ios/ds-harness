先验证当前目录基础测试和主线功能跨目录可用性：
主线测试全绿。验证 CLI 从子目录也能正常工作：
臣某谨奏

主线功能已确认跨目录可用：

- **子目录** `subdir/workbench`：本地测试通过，`mini_harness` 导入正常，pipeline 运行正常
- **仓库根**：全量 12 项 pytest 通过
- CLI 的 `_repo_root()` 基于 `__file__` 解析，不依赖 cwd，从任意子目录调用均可正确定位 `pyproject.toml`

当前无阻塞，等待进一步开发指示。

叩请圣裁