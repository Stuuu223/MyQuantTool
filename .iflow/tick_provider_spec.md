# TickProvider 统一封装规范

## 现状问题
- 脚本各自直接调用 xtdata/xtdatacenter
- 知识分散在 data_prefetch.py、download_wanzhu_tick_data.py、test_wangsu_*.py
- 每次新需求都重新摸索API

## 统一接口规范

```python
# logic/data_providers/tick_provider.py
class TickProvider:
    """唯一合法Tick数据提供者"""
    
    def __init__(self, config: TickConfig):
        self._init_xtdatacenter()  # 统一初始化
        
    def ensure_history(self, code: str, start: str, end: str) -> None:
        """确保本地有历史数据（必要时下载）"""
        
    def load_ticks(self, code: str, start: str, end: str) -> pd.DataFrame:
        """读取Tick数据（统一字段：lastPrice, volume, amount, bidPrice, askPrice）"""
        
    def get_coverage(self, code: str) -> Dict[str, List[str]]:
        """返回该票可用的日期范围（区分录制/回灌）"""
```

## 禁止事项（Code Review红线）
1. 禁止任何脚本直接 `import xtdata` 或 `import xtdatacenter`
2. 禁止脚本自己构造 `xtdc.set_token`、`xtdata.connect`
3. 禁止脚本直接操作 `QMT_DATA_DIR/datadir/SZ/0/` 路径

## 迁移计划
1. 实现 TickProvider 类
2. 迁移 download_wanzhu_tick_data.py 使用新接口
3. 迁移 t1_tick_backtester.py 使用新接口
4. 删除/归档旧脚本中的重复逻辑
5. 更新文档，明确唯一通路

## 验收标准
- 任何新脚本出现 xtdata import → PR直接拒绝
- 网宿1月26日Tick数据通过 `provider.load_ticks()` 一行代码获取
- 顽主131只票批量下载通过统一接口完成
