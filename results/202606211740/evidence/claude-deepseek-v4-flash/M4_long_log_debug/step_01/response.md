臣某谨奏

定位：`m4_noise_test.csv` 含 `#` 注释行，`csv.DictReader` 将首行 `# comment header` 当表头，后续 `ID,Name,Score` 字段超表头数 → 值变 `list`→ 在 `v.strip()` 处 crash。

修复：`read_csv` 前置 `_skip_comments()` 生成器过滤 `#` 注释行，并兼容 `restkey` 产生的 list 值。

核验：全部数据文件组合运行正常 — `m4_noise.csv` 2 processed / 1 rejected，`input.csv` 2/1，`events.jsonl` 2/1，三文件合并 6/3，三份 acceptance 报告一致（p=4, rj=2, rt=0）。

叩请圣裁