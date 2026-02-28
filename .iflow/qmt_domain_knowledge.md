# QMT 领域知识与数据契约 (绝对铁律)

> **警告：任何与 QMT `xtdata` 交互的代码，必须严格遵守以下数据结构与量纲约定。违背者直接视为重大生产事故！**

## 1. 历史日 K 线 (period='1d') 的数据结构

调用 `xtdata.get_local_data(..., period='1d')` 获取历史日线时：

- `volume` (成交量)：单位是 **【手】** (1手 = 100股)。
- `amount` (成交额)：单位是 **【元】**。
- `preClose` (昨收)：单位是 **【元】**。

**换算铁律**：在与流通股本（股）计算换手率时，必须执行 `(volume * 100) / float_volume`！

## 2. 历史 Tick (period='tick') 的数据结构

调用 `xtdata.get_local_data(..., period='tick')` 获取历史切片时：

- `volume` (成交量)：单笔成交量，单位是 **【手】**！
- `lastPrice` (最新价) / `price`：单位是 **【元】**。
- `time` (时间)：这是一个极度危险的异构字段！
  - 它通常是 **`int64` 类型的【毫秒级时间戳】**（例如 `1704072600000`）。
  - 它偶尔会是 `str` 类型的字符串（例如 `"09:30:00"`）。
  - **清洗铁律**：绝不能直接与 `'09:35:00'` 比较！必须通过统一的时间转换器清洗为纯字符串后，再做字符串比较！

## 3. 股票基础信息 (Instrument Detail)

调用 `xtdata.get_instrument_detail(stock_code)` 时：

- `FloatVolume` (流通股本)：这是一个巨坑！它的单位通常是 **【万股】或【股】**，不同的券商版本表现不同！
- **自适应铁律**：计算时，不要硬除 10000。必须通过 `models.py` 的 DTO 整流罩（自适应判断结果是否在 0~100 之间）来动态纠偏！

## 4. 架构隔离铁律 (分离关注点)

- **下载层**：只有 `tools/unified_downloader.py` 有权调用 `download_history_data` 和 `start_vip_service`。
- **回测层**：`TimeMachineEngine` **绝对禁止**调用下载函数！如果 `get_local_data` 查不到数据，直接在日志打印"本地未找到该日期的 xxx 数据"，然后 `continue`！绝不允许在算分时试图连接网络！

## 5. 数据目录路径

- QMT 数据统一读写根目录：`H:\QMT\userdata_mini\datadir` (底层为 C++ 维护的 .dat 数据库，严禁手动去拼凑 day/tick 等子目录！)

## 6. 量纲计算铁律（CTO 强制）

### 量比计算
```python
# 量比 = 当前量 / 5日均量 (同源相除，单位自动抵消)
vol_ratio = current_volume / avg_volume_5d
```

### 换手率计算
```python
# QMT实测：日K volume单位是手，FloatVolume单位是股
# 正确换手率 = (volume手 * 100 / FloatVolume股) * 100%
turnover = (current_volume * 100 / float_volume) * 100
```

### 资金流计算
```python
# Tick资金流 = (价格变化 * 成交量)
# 需要先统一单位：volume(手) * 100 = volume(股)
estimated_flow = price_change * (volume * 100)
```

## 7. 时间处理铁律（CTO 强制）

### Tick时间清洗
```python
def safe_parse_time(val):
    """万能时间解析器 - 支持毫秒时间戳和字符串"""
    if isinstance(val, str):
        if ':' in val: return val[-8:]  # 截取HH:MM:SS
    
    try:
        num_val = float(val)
        if num_val == 0: return '09:30:00'
        if num_val > 20000000000:  # 毫秒时间戳
            return datetime.fromtimestamp(num_val/1000.0).strftime('%H:%M:%S')
        else:  # 秒时间戳
            return datetime.fromtimestamp(num_val).strftime('%H:%M:%S')
    except:
        return '09:30:00'
```

### 时间比较铁律
```python
# ❌ 错误：直接比较时间戳和字符串
if curr_time == '09:45:00':  # 错误！curr_time可能是毫秒时间戳

# ✅ 正确：先清洗为统一格式
curr_time_str = safe_parse_time(curr_time)
if curr_time_str == '09:45:00':  # 正确！都是字符串
```

## 8. 违规惩罚机制

任何违背以上铁律的代码，将面临以下惩罚：
1. **立即拒绝**：CTO会直接拒绝合并
2. **代码重写**：全部重写，不留任何妥协
3. **记录黑名单**：违规者被记入代码审查黑名单

---

**最后警告**：这些不是建议，是铁律！违反任何一条，都会导致系统崩溃或计算错误！