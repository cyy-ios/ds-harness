# Memory Summary

早期设计决策：CLI 使用 `run` 子命令；配置文件是可选输入；内部路径统一从 repo root 解析；report 阶段只读取 clean 后的数据和 rejects。
历史偏好：测试先覆盖失败重试和 rejects，再扩展报告字段。
最近一次手工记录：所有 M1-M6 测试均通过、retry_count=1、外部缓存已写入。
