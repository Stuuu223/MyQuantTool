# MyQuantTool 核心阈值与配置手册 (SSOT)

## 唯一真理之源 (SSOT)
本系统所有交易阈值必须且只能从 `config/strategy_params.json` 读取。**严禁在代码中硬编码任何魔法数字（Magic Numbers）！**

## 核心配置项 (live_sniper 模块)
- **min_volume_multiplier**: `3.0` (起爆门槛：3倍量比)
- **turnover_rate_max**: `300.0` (死亡拦截：防量纲计算错误或诈尸)
- **min_active_turnover_rate**: `5.0` (起步换手：过滤死水僵尸股)

## 标准启动命令
```bash
python main.py live --mode real
```