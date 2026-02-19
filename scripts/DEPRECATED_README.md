# Scripts 目录整改说明 (PR-1)

## 整改时间
2026-02-19

## 删除文件清单

### V15迁移脚本（5个）
- v15_data_providers_merge.py
- v15_duplicate_merge.py  
- v15_fix_imports.py
- v15_precise_cleanup.py

### 一次性脚本（3个）
- apply_wanzhu_mapping.py（映射已完成）
- select_wanzhu_big_movers.py（功能重复）
- map_wanzhu_names_to_codes.py（已归档）

### 测试/启动脚本（9个）
- test_*.bat/ps1 (4个)
- start_*.bat/ps1 (5个，保留start_quant_system.bat)

### 分析脚本（1个）
- wanzhu_halfway_analyzer.py（分析完成）

### 其他（1个）
- TICK_DOWNLOAD_SHUTDOWN_README.md

## 替代方案

| 旧脚本 | 新入口 |
|--------|--------|
| download_*.py (9个) | scripts/download_manager.py |
| check_*.py (4个) | scripts/system_check.py |
| monitor_*.py (3个) | scripts/monitor_runner.py |
| generate_*_report.py (2个) | tasks/generate_report.py |
| run_*_scan.py (4个) | tasks/run_scan.py |

## 迁移中的Wrapper

被删除但外部可能依赖的脚本，已添加wrapper提示：
```python
raise RuntimeError(
    "此脚本已废弃，请使用新入口：\n"
    "  python scripts/download_manager.py --help"
)
```
