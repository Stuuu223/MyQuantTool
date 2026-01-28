# QMT 接口使用说明

## 🎯 你需要知道

**QMT 数据接口可以作为额外的数据源，但不是必需的！**

你的项目已经有：
- ✅ **easyquotation** - 实时行情（主要数据源）
- ✅ **AkShare** - 市场数据（已在使用）
- ✅ **QMT xtdata** - 备用数据源（可选）

## 📊 QMT 数据接口特点

### 优点
- 数据质量高
- 提供历史K线数据
- 可以获取财务数据
- 速度快

### 缺点
- 首次使用需要下载数据
- 某些功能需要QMT客户端支持

## 🚀 使用方式

### 方式1：作为独立数据源（推荐）
不需要启动QMT客户端，直接使用：

```python
from xtquant import xtdata

# 获取股票列表
stock_list = xtdata.get_stock_list_in_sector('沪深A股')

# 下载历史数据
xtdata.download_history_data('600519.SH', period='1d',
                             start_time='20240101', end_time='20240131')

# 获取本地数据
data = xtdata.get_local_data(
    field_list=['time', 'open', 'high', 'low', 'close'],
    stock_list=['600519.SH'],
    period='1d',
    start_time='20240101',
    end_time='20240131'
)
```

### 方式2：作为实时数据源
需要启动QMT客户端（可选）：

```python
from xtquant import xtdata

# 获取实时tick数据
tick_data = xtdata.get_full_tick(['600519.SH'])
```

## 💡 最佳实践

### 建议的数据源优先级

1. **实时行情**：使用 easyquotation（你已经在用）
2. **历史数据**：使用 AkShare（你已经在用）
3. **备用数据**：使用 QMT xtdata（可选）

### 什么时候使用QMT？

- ✅ 需要高质量的历史K线数据
- ✅ 需要获取财务数据
- ✅ easyquotation/AkShare 数据不足时作为备用
- ✅ 需要某些特定数据（如板块、指数权重等）

### 什么时候不用QMT？

- ❌ 只需要实时行情（用 easyquotation）
- ❌ 不需要额外数据源
- ❌ 不想下载额外数据

## 🔧 快速测试

```bash
# 测试QMT数据接口
python test_qmt_connection.py
```

如果测试失败，不影响你的系统运行，因为你有其他数据源。

## 📝 总结

**QMT是可选的，不是必需的！**

- 主要数据源：easyquotation + AkShare
- QMT作为补充数据源
- 交易接口已禁用（不需要实盘交易）

放心使用你的系统，QMT只是一个额外的数据选项。