# ⚖️ MyQuantTool 系统宪法与开发铁律 (V20 终极防线)

> **警告：任何人、任何 Agent、任何 AI 助手，在修改代码前必须熟读并宣誓遵守本宪法。违背以下任意一条，直接判定为严重工程事故！**

**版本**: V20.0.0 (CTO终极防线版)  
**生效日期**: 2026-02-28  
**制定者**: CTO + Boss  
**执行者**: AI开发团队

---

## 🛑 第一防线：时空与未来函数铁律

### 1.1 严禁"时空穿透" (Look-ahead Bias)
**绝对禁止**: 回测引擎 (`TimeMachineEngine`) 调取任何历史均量、历史 ATR 时**不传 `target_date`**！  
**唯一正确**: 所有历史数据查询必须强传 `target_date`，确保使用历史日期的数据而非当前日期。  
**惩罚**: 用今天的数据去算去年的得分，直接自毁！

**示例**:
```python
# ❌ 错误 - 时空穿透！用今天数据算历史
avg_volume = true_dict.get_avg_volume_5d(stock_code)  # 默认取今天！

# ✅ 正确 - 严格传入target_date
avg_volume = true_dict.get_avg_volume_5d(stock_code, target_date=date)
```

### 1.2 严禁"自然日推算"
**绝对禁止**: 使用 `timedelta(days=1)` 推算"昨天"！  
**唯一正确**: 必须且只能调用 `calendar_utils.py` 中的 QMT 原生交易日历。  
**惩罚**: 周末减一天得到周五，跨节假日会陷入数据黑洞！

**示例**:
```python
# ❌ 错误 - 自然日推算会踩坑周末
prev_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

# ✅ 正确 - QMT原生交易日历
from logic.utils.calendar_utils import get_previous_trading_day
prev_date = get_previous_trading_day(today_str)
```

### 1.3 全天候时空锁
**绝对强制**: 实盘引擎的 `run()` 方法第一行，必须进行非交易日/盘后拦截！  
**惩罚**: 严禁在周末启动死循环火控！严禁在15:00后启动实盘监控！

**示例**:
```python
# ✅ 正确 - main.py live_cmd开头必须拦截
if not is_trading_day(today_str):
    click.echo("🛑 今天是非交易日！禁止启动实盘！")
    return  # 绝对禁止继续！
```

---

## 🛑 第二防线：数据真理与强类型铁律

### 2.1 数据造假零容忍
**绝对禁止**: 当 `avg_volume_5d` 或任何数据获取失败时，**硬编码塞入 `1.0` 或其他假数据兜底**！  
**唯一正确**: 算不出就 `continue` 跳过，宁可空榜，不可造假！  
**惩罚**: 假数据会导致错误信号，造成真金白银的亏损！

**示例**:
```python
# ❌ 错误 - 数据造假！
if not avg_volume_5d:
    avg_volume_5d = 1.0  # 假数据！罪恶！

# ✅ 正确 - 算不出就跳过
if not avg_volume_5d or avg_volume_5d <= 0:
    continue  # 跳过这只票，宁可错过，不可做错
```

### 2.2 消除"类型爆炸" (Safe Float 护城河)
**绝对强制**: 从 QMT 字典或 JSON 读出的任何数据，在运算前**必须经过 `safe_float()` 强转**！  
**惩罚**: 彻底消灭 `'>' not supported between str and int` 这种弱智报错！

**示例**:
```python
# ❌ 错误 - 类型爆炸
if avg_volume_5d > 0:  # str > int 会崩溃！

# ✅ 正确 - safe_float护城河
def safe_float(val):
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0

avg_volume_5d = safe_float(avg_volume_5d)
if avg_volume_5d > 0:  # 现在安全了
```

### 2.3 单位必须对齐
**绝对强制**: QMT的 `volume` 是手，`FloatVolume` 是股！单位必须对齐！  
**惩罚**: 遇到换手率算出 `0.08%` 这种弱智极小值，必须自动检测并纠偏！

**示例**:
```python
# 换手率计算
float_volume = true_dict.get_float_volume(stock)  # 股
volume = tick_data['volume']  # 手

# 单位对齐
turnover_rate = (volume * 100 / float_volume) * 100  # 转为百分比

# 自动纠偏 - 如果<0.1%，说明单位错了
if turnover_rate < 0.1:
    turnover_rate = (volume * 10000 / float_volume) * 100  # 重新算
```

### 2.4 死亡换手率全局统一
**强制标准**: 死亡换手率全局统一为 **70%**！  
**惩罚**: 严禁各处使用不同阈值（60%、65%、70%混乱）！

---

## 🛑 第三防线：架构与行为规范铁律

### 3.1 垃圾文件焚烧法
**绝对禁止**: 根目录出现 `debug_xx.py`、`check_xx.py` 等野脚本！  
**唯一正确**: 测试一律进 `tests/`，临时脚本用完立刻删除！  
**惩罚**: 根目录只能有 `main.py` 和系统文档！

### 3.2 严禁捏造 API (幻觉隔离)
**绝对禁止**: 不确定的 QMT 接口时私自脑补 API！  
**唯一正确**: 必须查阅官方文档或现有代码，流通股本必须用 `get_instrument_detail`！  
**惩罚**: 严禁使用 `xtdata.get_stock_list()` 等不存在 API！

### 3.3 唯一事实来源 (SSOT)
**绝对强制**: 战地看板和全息龙榜必须使用同一个排序好的数据源！  
**惩罚**: 严禁存在两套打分引擎精神分裂！

### 3.4 零硬编码路径
**绝对禁止**: 任何 `E:\`、`C:\`、`./`、`../` 开头的路径字符串！  
**唯一正确**: 所有路径通过 `PathResolver` 动态解析！

### 3.5 Fail Fast 原则
**绝对禁止**: `try-except-pass` 静默吞没异常！  
**唯一正确**: 异常立即抛出，禁止返回 `None` 代替错误！

---

## 🛑 第四防线：计算基准铁律

### 4.1 真实涨幅计算
**绝对禁止**: 使用 `(收盘价-开盘价)/开盘价` 计算涨幅！  
**唯一正确**: `(今收-昨收)/昨收`，必须使用 `pre_close`！

### 4.2 真实振幅计算
**绝对禁止**: 使用当日最高最低价差除以当日开盘价！  
**唯一正确**: `(最高-最低)/昨收`！

### 4.3 昨收价获取
**绝对禁止**: 使用任何外部API或估算值！  
**唯一正确**: QMT本地日线数据 `xtdata.get_local_data()`！

---

## 📋 审查清单 (Checklist)

提交代码前必须逐项确认：

- [ ] 没有使用 `timedelta(days=1)` 推算日期
- [ ] 所有历史数据查询都传了 `target_date`
- [ ] 所有从QMT读出的数据都经过 `safe_float()`
- [ ] 没有硬编码假数据兜底
- [ ] 换手率单位已对齐
- [ ] 死亡换手率统一为70%
- [ ] 没有在根目录创建临时文件
- [ ] 没有捏造不存在的API
- [ ] 没有硬编码路径
- [ ] 异常处理没有静默吞没

---

**本宪法具有最高法律效力。违反者，代码拒绝合并；屡犯者，回滚重来！**
