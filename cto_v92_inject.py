# -*- coding: utf-8 -*-
"""
CTO V92 物理引擎升级 - 指数速度场与纯度断头台
"""
import re

print("=" * 60)
print("CTO V92 指数级杀戮场物理引擎升级")
print("=" * 60)

file_path = "logic/strategies/kinetic_core_engine.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 找到函数定义
func_pattern = r'def calculate_true_dragon_score\('
match = re.search(func_pattern, content)

if not match:
    print("ERROR: 未找到 calculate_true_dragon_score 函数!")
    exit(1)

# 找到函数签名结束位置（docstring之后）
func_start = match.start()
lines = content[func_start:].split('\n')

# 找到第一个非docstring、非空行的代码开始
code_start_idx = 0
in_docstring = False
docstring_char = None

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # 检测docstring开始
    if not in_docstring:
        if stripped.startswith('"""') or stripped.startswith("'''"):
            docstring_char = stripped[0]*3
            if stripped.count(docstring_char) >= 2:
                # 单行docstring
                in_docstring = False
            else:
                in_docstring = True
            continue
        elif stripped and not stripped.startswith('#'):
            # 找到第一个代码行
            code_start_idx = i
            break
    else:
        # 在docstring内，检查结束
        if docstring_char in line:
            in_docstring = False
            continue

# 找到下一个方法定义
next_def_match = re.search(r'\n    def ', content[func_start + sum(len(l)+1 for l in lines[:code_start_idx]):])
if next_def_match:
    end_idx = func_start + sum(len(l)+1 for l in lines[:code_start_idx]) + next_def_match.start()
else:
    end_idx = len(content)

# 新的V92物理引擎代码
new_logic = '''        import math
        # === 【CTO V92 绝对杀戮场：指数速度与纯度断头台】 ===
        
        # 安全转换
        net_inflow = safe_float(net_inflow, 0.0)
        price = safe_float(price, 0.0)
        prev_close = safe_float(prev_close, 0.0)
        high = safe_float(high, 0.0)
        low = safe_float(low, 0.0)
        open_price = safe_float(open_price, 0.0)
        flow_5min = safe_float(flow_5min, 0.0)
        flow_15min = safe_float(flow_15min, 0.0)
        flow_5min_median_stock = safe_float(flow_5min_median_stock, 2_000_000)
        float_volume_shares = safe_float(float_volume_shares, 0.0)
        
        # 安全检查
        if price <= 0 or prev_close <= 0:
            return 0.0, 0.0, 0.0, 0.0, 0.0
        if float_volume_shares <= 0:
            return 0.0, 0.0, 0.0, 0.0, 0.0
        if high < low:
            high = low = price
        
        # 量纲升维
        float_market_cap = float_volume_shares * price
        if 0 < float_market_cap < 200000000:
            float_market_cap = float_market_cap * 10000.0
        
        # ========== 1. 涨幅计算 ==========
        change_pct = (price - prev_close) / prev_close * 100.0
        
        # ========== 2. 质量 = 流入占比 * 放量倍数 ==========
        if float_market_cap > 1000:
            raw_inflow_pct = (net_inflow / float_market_cap * 100.0)
            if abs(raw_inflow_pct) > 30.0:
                sign = 1.0 if raw_inflow_pct > 0 else -1.0
                inflow_ratio_pct = sign * (30.0 + 10.0 * math.log10(abs(raw_inflow_pct) - 29.0))
            else:
                inflow_ratio_pct = raw_inflow_pct
        else:
            inflow_ratio_pct = 0.0
        
        MIN_BASE_FLOW = 2_000_000
        safe_flow_5min = flow_5min if flow_5min > 0 else (flow_15min / 3.0 if flow_15min > 0 else 1.0)
        safe_median = flow_5min_median_stock if flow_5min_median_stock > 0 else MIN_BASE_FLOW
        raw_ratio_stock = safe_flow_5min / safe_median if safe_median > 0 else 1.0
        ratio_stock = 1.0 + 6.0 * math.tanh(raw_ratio_stock - 1.0)
        
        mass_potential = (inflow_ratio_pct / 100.0) * ratio_stock
        
        # ========== 3. 指数速度向量 (VELOCITY CUBED) ==========
        # 【CTO V92 铁律】涨幅的威力是非线性的！3次幂让涨幅9%的动能是涨幅3%的27倍！
        sign_velocity = 1.0 if change_pct >= 0 else -1.0
        velocity = sign_velocity * (abs(change_pct) ** 3)
        
        # ========== 4. 基础动能 ==========
        base_kinetic_energy = mass_potential * velocity
        
        # ========== 5. 纯度断头台 (MICRO-MOMENTUM GUILLOTINE) ==========
        price_range = high - low
        if price_range > 0:
            raw_purity = (price - low) / price_range
        else:
            raw_purity = 1.0 if change_pct > 0 else 0.0
        purity_norm = min(max(raw_purity, 0.0), 1.0)
        
        # 【断崖式大摆锤】真龙纯度必须极高！
        # 低于70%开始遭遇指数级剥夺，低于50%直接灰飞烟灭！
        # 使用5次幂衰减: 纯度0.9->0.59, 纯度0.7->0.16(绞杀84%), 纯度0.5->0.03(绞杀97%)
        friction_multiplier = purity_norm ** 5
        
        # ========== 6. MFE效率激活场 ==========
        if inflow_ratio_pct <= 0.0:
            efficiency_multiplier = 0.0
            mfe = 0.0
        else:
            upward_thrust = ((price - low) + (high - open_price)) / 2
            price_range_pct = upward_thrust / prev_close * 100.0 if prev_close > 0 else 0.0
            mfe = price_range_pct / inflow_ratio_pct if inflow_ratio_pct > 0 else 0.0
            efficiency_multiplier = 3.0 / (1.0 + math.exp(-2.0 * (mfe - 1.2)))
        
        # ========== 7. 终极融合 ==========
        final_score_raw = base_kinetic_energy * friction_multiplier * efficiency_multiplier
        # 为了抵消3次方带来的数值膨胀，缩小标度
        final_score = round(final_score_raw / 10.0, 1)
        if final_score < 0:
            final_score = 0.0
        
        # Sustain计算（兼容输出）
        safe_median_15min = flow_5min_median_stock * 3.0 if flow_5min_median_stock > 0 else MIN_BASE_FLOW * 3.0
        sustain_ratio = flow_15min / safe_median_15min if safe_median_15min > 0 else 0.0
        float_mc_yi = float_market_cap / 100000000.0
        if float_mc_yi > 0:
            gravity_damper = min(max(1.0 + math.log10(float_mc_yi / 50.0) * 0.5, 0.5), 2.5)
        else:
            gravity_damper = 0.5
        sustain_ratio = sustain_ratio * gravity_damper
        
        return final_score, sustain_ratio, inflow_ratio_pct, ratio_stock, mfe
'''

# 组装新内容
new_content = content[:func_start + sum(len(l)+1 for l in lines[:code_start_idx])] + new_logic + content[end_idx:]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("OK: V92 指数级断头台物理算子注入成功!")
print("  - 速度向量: 线性 -> 3次方指数")
print("  - 纯度阻尼: 2次方 -> 5次方断头台")
print("  - 纯度0.7 -> 绞杀84%分数")
print("  - 纯度0.55 -> 绞杀97%分数")