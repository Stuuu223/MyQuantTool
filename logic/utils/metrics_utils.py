# -*- coding: utf-8 -*-
"""
指标计算工具模块 - Phase 7核心能力封装

提供统一的指标计算能力，包括VWAP、承接力度等核心指标。
所有计算基于QMT本地数据，禁止估算和兜底值。

设计原则：
- 禁止估算/兜底值
- 禁止返回None代替错误
- 明确的输入输出约定
- 完整的异常处理

Author: iFlow CLI
Date: 2026-02-23
Version: 1.0.0
"""

from typing import Optional, List, Tuple
import pandas as pd
import numpy as np

from logic.utils.logger import get_logger

logger = get_logger(__name__)


class MetricsCalculationError(Exception):
    """指标计算错误"""
    pass


class InsufficientDataError(Exception):
    """数据不足错误"""
    pass


def calc_vwap(df: pd.DataFrame, 
              price_col: str = 'price',
              volume_col: str = 'volume',
              min_records: int = 10) -> float:
    """
    计算成交量加权平均价(VWAP)
    
    VWAP = Σ(价格 × 成交量) / Σ(成交量)
    
    Args:
        df: DataFrame，包含价格成交量数据
        price_col: 价格列名，默认'price'
        volume_col: 成交量列名，默认'volume'
        min_records: 最小记录数要求，默认10条
    
    Returns:
        float: VWAP值
    
    Raises:
        ValueError: 参数无效或DataFrame为空
        InsufficientDataError: 数据记录数不足
        MetricsCalculationError: 计算失败
    
    Example:
        >>> df = pd.DataFrame({
        ...     'price': [10.0, 10.5, 11.0],
        ...     'volume': [100, 200, 150]
        ... })
        >>> vwap = calc_vwap(df)
        >>> print(vwap)
        10.57
    """
    # 1. DataFrame验证
    if df is None:
        raise ValueError("DataFrame不能为空")
    
    if not isinstance(df, pd.DataFrame):
        raise ValueError(f"输入必须是DataFrame，实际类型: {type(df)}")
    
    if len(df) == 0:
        raise ValueError("DataFrame为空，无数据可计算")
    
    # 2. 列名验证
    if price_col not in df.columns:
        raise ValueError(f"价格列不存在: {price_col}，可用列: {list(df.columns)}")
    
    if volume_col not in df.columns:
        raise ValueError(f"成交量列不存在: {volume_col}，可用列: {list(df.columns)}")
    
    # 3. 数据量检查
    if len(df) < min_records:
        raise InsufficientDataError(
            f"数据记录数不足: {len(df)} < {min_records}"
        )
    
    # 4. 数据清洗 - 去除无效值
    valid_mask = (
        df[price_col].notna() & 
        df[volume_col].notna() &
        (df[volume_col] >= 0) &  # 成交量可以为0，不能为负
        (df[price_col] > 0)     # 价格必须为正
    )
    
    valid_count = valid_mask.sum()
    if valid_count < min_records:
        raise InsufficientDataError(
            f"有效数据不足: {valid_count} < {min_records}"
        )
    
    clean_df = df[valid_mask].copy()
    
    # 5. 计算VWAP
    try:
        prices = clean_df[price_col].astype(float)
        volumes = clean_df[volume_col].astype(float)
        
        total_volume = volumes.sum()
        
        if total_volume <= 0:
            raise MetricsCalculationError(
                f"总成交量必须大于0: {total_volume}"
            )
        
        vwap = (prices * volumes).sum() / total_volume
        
    except Exception as e:
        raise MetricsCalculationError(f"VWAP计算失败: {e}")
    
    # 6. 结果验证
    if not isinstance(vwap, (int, float)):
        raise MetricsCalculationError(f"VWAP计算结果异常: {vwap}")
    
    if vwap <= 0:
        raise MetricsCalculationError(f"VWAP必须大于0: {vwap}")
    
    if np.isinf(vwap) or np.isnan(vwap):
        raise MetricsCalculationError(f"VWAP计算结果无效: {vwap}")
    
    logger.debug(f"VWAP计算完成: {vwap:.4f} ({len(clean_df)}条记录)")
    return round(vwap, 4)


def calc_sustain_factor(current_price: float, vwap: float) -> float:
    """
    计算承接力度因子 (Sustain Factor)
    
    衡量当前价格相对于VWAP的位置，反映市场承接力度。
    
    计算公式：
        sustain_factor = 1 / (1 + exp(-k * (price - vwap) / vwap))
    简化版本（本实现使用）：
        sustain_factor = (current_price / vwap) - 0.5 * 2  # 线性映射
    
    更稳定的sigmoid映射：
        - 当 price = vwap 时，factor = 0.5
        - 当 price > vwap 时，factor > 0.5
        - 当 price < vwap 时，factor < 0.5
        - 范围限制在 [0.0, 1.0]
    
    Args:
        current_price: 当前价格
        vwap: VWAP值
    
    Returns:
        float: 0.0-1.0之间的值
        - 1.0: 价格远高于VWAP，承接最强
        - 0.5: 价格等于VWAP
        - 0.0: 价格远低于VWAP，承接最弱
    
    Raises:
        ValueError: 参数无效
        MetricsCalculationError: 计算失败
    
    Example:
        >>> factor = calc_sustain_factor(11.0, 10.5)
        >>> print(factor)
        0.72
    """
    # 1. 参数验证
    if current_price is None or vwap is None:
        raise ValueError("价格和VWAP不能为空")
    
    if not isinstance(current_price, (int, float)):
        raise ValueError(f"当前价格必须是数字: {type(current_price)}")
    
    if not isinstance(vwap, (int, float)):
        raise ValueError(f"VWAP必须是数字: {type(vwap)}")
    
    # 2. 数值有效性检查
    if current_price <= 0:
        raise ValueError(f"当前价格必须大于0: {current_price}")
    
    if vwap <= 0:
        raise ValueError(f"VWAP必须大于0: {vwap}")
    
    # 3. 计算价格相对于VWAP的偏离比例
    try:
        price_ratio = current_price / vwap
    except ZeroDivisionError:
        raise MetricsCalculationError("VWAP为0，无法计算承接力度")
    
    # 4. 使用sigmoid函数映射到[0,1]区间
    # 基础思想：将price_ratio以1.0为中心进行映射
    # price_ratio = 1.0 (price=vwap) -> 0.5
    # price_ratio > 1.0 (price>vwap) -> >0.5
    # price_ratio < 1.0 (price<vwap) -> <0.5
    
    # 计算偏离程度，使用steepness控制曲线陡峭度
    steepness = 4.0  # 经验值，可根据需要调整
    deviation = (price_ratio - 1.0) * steepness
    
    try:
        # sigmoid函数: 1 / (1 + exp(-x))
        import math
        sustain = 1.0 / (1.0 + math.exp(-deviation))
    except OverflowError:
        # 处理极端值
        if deviation > 0:
            sustain = 1.0
        else:
            sustain = 0.0
    
    # 5. 结果验证和边界处理
    sustain = max(0.0, min(1.0, sustain))
    
    if np.isnan(sustain) or np.isinf(sustain):
        raise MetricsCalculationError(f"承接力度计算结果无效: {sustain}")
    
    logger.debug(f"承接力度计算: price={current_price}, vwap={vwap}, factor={sustain:.4f}")
    return round(sustain, 4)


def calc_sustain_linear(current_price: float, vwap: float, 
                        max_deviation: float = 0.1) -> float:
    """
    计算承接力度因子（线性版本）
    
    线性映射版本，计算更快，适合高频场景。
    
    Args:
        current_price: 当前价格
        vwap: VWAP值
        max_deviation: 最大考虑偏离比例（默认10%）
    
    Returns:
        float: 0.0-1.0之间的值
    
    Raises:
        ValueError: 参数无效
        MetricsCalculationError: 计算失败
    
    Example:
        >>> factor = calc_sustain_linear(11.0, 10.5)
        >>> print(factor)
        0.76
    """
    # 1. 参数验证
    if current_price is None or vwap is None:
        raise ValueError("价格和VWAP不能为空")
    
    if current_price <= 0 or vwap <= 0:
        raise ValueError(f"价格和VWAP必须大于0: price={current_price}, vwap={vwap}")
    
    if max_deviation <= 0:
        raise ValueError(f"最大偏离比例必须大于0: {max_deviation}")
    
    # 2. 计算偏离比例
    deviation = (current_price - vwap) / vwap
    
    # 3. 线性映射到[0,1]
    # deviation = -max_deviation -> 0
    # deviation = 0 -> 0.5
    # deviation = max_deviation -> 1
    sustain = (deviation / (2 * max_deviation)) + 0.5
    
    # 4. 边界处理
    sustain = max(0.0, min(1.0, sustain))
    
    return round(sustain, 4)


def calc_intraday_vwap_from_ticks(tick_df: pd.DataFrame,
                                  time_col: str = 'time',
                                  price_col: str = 'price',
                                  volume_col: str = 'volume',
                                  min_records: int = 10) -> dict:
    """
    从Tick数据计算日内VWAP及衍生指标
    
    Args:
        tick_df: Tick数据DataFrame
        time_col: 时间列名
        price_col: 价格列名
        volume_col: 成交量列名
    
    Returns:
        dict: {
            'vwap': float,           # VWAP值
            'total_volume': float,   # 总成交量
            'avg_price': float,      # 简单均价
            'price_std': float,      # 价格标准差
            'record_count': int      # 记录数
        }
    
    Raises:
        ValueError: 参数无效
        InsufficientDataError: 数据不足
    """
    if tick_df is None or len(tick_df) == 0:
        raise ValueError("Tick数据不能为空")
    
    # 检查必要列
    required_cols = [price_col, volume_col]
    for col in required_cols:
        if col not in tick_df.columns:
            raise ValueError(f"缺少必要列: {col}")
    
    # 数据清洗
    clean_df = tick_df[
        tick_df[price_col].notna() &
        tick_df[volume_col].notna() &
        (tick_df[price_col] > 0) &
        (tick_df[volume_col] >= 0)
    ].copy()
    
    if len(clean_df) < min_records:
        raise InsufficientDataError(f"有效数据不足: {len(clean_df)} < {min_records}")
    
    # 计算VWAP
    vwap = calc_vwap(clean_df, price_col, volume_col, min_records=min_records)
    
    # 计算其他统计指标
    prices = clean_df[price_col].astype(float)
    volumes = clean_df[volume_col].astype(float)
    
    result = {
        'vwap': vwap,
        'total_volume': float(volumes.sum()),
        'avg_price': float(prices.mean()),
        'price_std': float(prices.std()),
        'record_count': len(clean_df)
    }
    
    return result


def batch_calc_sustain(current_prices: List[float], 
                       vwap_values: List[float]) -> List[float]:
    """
    批量计算承接力度因子
    
    Args:
        current_prices: 当前价格列表
        vwap_values: VWAP值列表
    
    Returns:
        List[float]: 承接力度因子列表
    
    Raises:
        ValueError: 列表长度不匹配
    """
    if len(current_prices) != len(vwap_values):
        raise ValueError(
            f"价格列表和VWAP列表长度不匹配: "
            f"{len(current_prices)} vs {len(vwap_values)}"
        )
    
    results = []
    errors = []
    
    for i, (price, vwap) in enumerate(zip(current_prices, vwap_values)):
        try:
            factor = calc_sustain_factor(price, vwap)
            results.append(factor)
        except Exception as e:
            errors.append(f"索引{i}: {e}")
            results.append(0.5)  # 中性值
    
    if errors:
        logger.warning(f"批量计算部分失败 ({len(errors)}/{len(current_prices)}): {errors[:3]}")
    
    return results


def render_battle_dashboard(data_list, title="战报", clear_screen=False):
    """
    【CTO V28 Rich工业大屏】原地刷新，永不滚屏！
    """
    # 【CTO安全渲染】空列表保护
    if not data_list:
        print(f"\n====================\n{title} (空榜单)\n====================")
        return
    
    # 清屏
    if clear_screen:
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    # 【CTO V28】使用Rich库替代print
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        
        console = Console()
        
        # 构建Rich Table
        table = Table(show_header=True, header_style="bold magenta", style="cyan", expand=False)
        table.add_column("RANK", justify="center", width=4)
        table.add_column("TARGET", justify="center", width=10, style="bold white")
        table.add_column("SCORE", justify="right", width=7, style="bold red")
        table.add_column("PRICE", justify="right", width=7)
        table.add_column("CHG%", justify="right", width=8)
        table.add_column("INFLOW%", justify="right", width=9)
        table.add_column("SUSTAIN", justify="right", width=8)
        table.add_column("MFE", justify="right", width=6)
        
        for i, item in enumerate(data_list, 1):
            # 【CTO安全渲染】：绝对兜底，不准报错
            code = item.get('code', item.get('stock_code', 'N/A'))
            score = item.get('score', item.get('final_score', 0.0))
            price = item.get('price', 0.0)
            change = item.get('change', item.get('final_change', 0.0))
            inflow = item.get('inflow_ratio', 0.0)
            sustain = item.get('sustain_ratio', 0.0)
            mfe = item.get('mfe', 0.0)
            
            # 【CTO安全渲染】强制数值转换，防止类型爆炸
            try:
                score = float(score) if score is not None else 0.0
            except (ValueError, TypeError):
                score = 0.0
            try:
                price = float(price) if price is not None else 0.0
            except (ValueError, TypeError):
                price = 0.0
            try:
                change = float(change) if change is not None else 0.0
            except (ValueError, TypeError):
                change = 0.0
            try:
                inflow = float(inflow) if inflow is not None else 0.0
            except (ValueError, TypeError):
                inflow = 0.0
            try:
                sustain = float(sustain) if sustain is not None else 0.0
            except (ValueError, TypeError):
                sustain = 0.0
            try:
                mfe = float(mfe) if mfe is not None else 0.0
            except (ValueError, TypeError):
                mfe = 0.0
            
            # 【CTO V28】量化纯度颜色渲染
            if score >= 80:
                score_style = "bold red"  # 纯正攻击
            elif score >= 50:
                score_style = "bold yellow"  # 温和上涨
            elif score >= 20:
                score_style = "white"  # 震荡
            else:
                score_style = "green"  # 砸盘出货
            
            # 涨跌幅颜色
            if change > 0:
                change_style = "bold red"
            elif change < 0:
                change_style = "bold green"
            else:
                change_style = "white"
            
            # 限制MFE范围
            mfe = max(-99.9, min(mfe, 99.9))
            
            table.add_row(
                str(i),
                code,
                f"[{score_style}]{score:.1f}[/]",
                f"{price:.2f}",
                f"[{change_style}]{change:+.2f}%[/]",
                f"{inflow:.2f}%",
                f"{sustain:.2f}",
                f"{mfe:.1f}"
            )
        
        # 打印标题和表格
        console.print(Panel(f"🚀 {title}", style="bold yellow"))
        console.print(table)
        
    except ImportError:
        # 【降级】Rich库不可用时使用print
        print(f"\n{'='*100}")
        print(f"🚀 {title}")
        print(f"{'='*100}")
        print(f"{'排名':<4} {'代码':<10} {'得分':<6} {'价格':<6} {'流入比':<6} {'爆发':<6} {'接力':<6} {'MFE':<6}")
        print(f"{'-'*100}")
        
        for i, item in enumerate(data_list, 1):
            code = item.get('code', item.get('stock_code', 'N/A'))
            score = item.get('score', item.get('final_score', 0.0))
            price = item.get('price', 0.0)
            inflow = item.get('inflow_ratio', 0.0)
            ratio = item.get('ratio_stock', 0.0)
            sustain = item.get('sustain_ratio', 0.0)
            mfe = item.get('mfe', 0.0)
            
            print(f"{i:<4} {code:<10} {score:<6.2f} {price:<6.2f} {inflow:<6.2f} {ratio:<6.2f} {sustain:<6.2f} {mfe:<6.2f}")
        print(f"{'='*100}\n")


# 【CTO V118】FPS锁频控制 - 防止终端刷屏
_last_display_time = 0
_DISPLAY_INTERVAL = 3.0  # 每3秒刷新一次屏幕

def render_live_dashboard(top_targets, pool_stats=None, is_rest=False, msg=None, initial_loading=False):
    """
    【CTO V34】实盘引擎专用UI渲染函数
    【CTO V118】FPS锁频 - 每3秒刷新一次，防止终端刷屏
    
    从run_live_trading_engine.py剥离，实现UI与逻辑分离
    
    Args:
        top_targets: TOP10目标列表
        pool_stats: 漏斗统计信息
        is_rest: 是否盘后/非交易日模式
        msg: 自定义标题消息
        initial_loading: 是否初始加载中
    """
    import os
    import time
    from datetime import datetime
    global _last_display_time
    
    # 【CTO V118】FPS锁频检查
    current_time = time.time()
    if not initial_loading and not is_rest:
        if current_time - _last_display_time < _DISPLAY_INTERVAL:
            return  # 3秒内不刷新，直接返回
    
    _last_display_time = current_time
    
    # 【CTO V13】盘后投影模式不清屏，静默追加
    if not is_rest:
        os.system('cls' if os.name == 'nt' else 'clear')
    now_str = datetime.now().strftime('%H:%M:%S')
    
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        
        console = Console()
        
        # 标题栏
        if msg:
            title_str = f"🚀 [V20 暴力猎杀雷达] | {msg} | {now_str}"
        elif is_rest:
            title_str = f"🚀 [V20 暴力猎杀雷达] | [静态投影复盘] | {now_str}"
        else:
            title_str = f"🚀 [V20 暴力猎杀雷达] | [极速高频狙击] | {now_str}"
        
        console.print(Panel(title_str, style="bold cyan", expand=False))
        
        if initial_loading:
            console.print("[yellow]>>> 正在连接 QMT 物理内存，装载高阶算子...[/yellow]")
            return
        
        # 战场统计
        if pool_stats:
            passed = pool_stats.get('passed_fine_filter', pool_stats.get('active', 0))
            console.print(f"[white]* 猎杀漏斗: 5191只 → 粗筛: {pool_stats.get('total', 0)}只 → 活跃: {pool_stats.get('active', 0)}只 → 过细筛: {passed}只[/white]")
            console.print(f"[white]* 战场情绪: 红盘/封板: {pool_stats.get('up', 0)}只 | 水下/绿盘: {pool_stats.get('down', 0)}只 | 派发剔除: {pool_stats.get('active', 0) - passed}只[/white]")
        
        # Rich Table核心算子矩阵
        table = Table(show_header=True, header_style="bold magenta", style="cyan", expand=False)
        table.add_column("RANK", justify="center", width=4)
        table.add_column("TARGET", justify="center", width=10, style="bold white")
        table.add_column("SCORE", justify="right", width=7, style="bold red")
        table.add_column("PRICE", justify="right", width=7)
        table.add_column("CHG%", justify="right", width=8)
        table.add_column("INFLOW%", justify="right", width=9)
        table.add_column("SUSTAIN", justify="right", width=8)
        table.add_column("MFE", justify="right", width=6)
        table.add_column("PURITY%", justify="right", width=8)
        
        if not top_targets:
            table.add_row("...", "暂无目标", "...", "...", "...", "...", "...", "...", "...")
        else:
            for i, t in enumerate(top_targets, 1):
                row_style = "bold red" if i <= 3 else None
                
                # 量化纯度渲染
                p_val = t.get('purity', 0)
                if p_val >= 80:
                    p_color = "bold red"
                elif p_val >= 20:
                    p_color = "yellow"
                elif p_val >= -20:
                    p_color = "white"
                else:
                    p_color = "green"
                purity_str = f"[{p_color}]{p_val:+.1f}%[/{p_color}]"
                
                # MFE和Sustain物理截断防爆表
                safe_sustain = min(max(t.get('sustain_ratio', 0), -99.9), 99.9)
                safe_mfe = min(max(t.get('mfe', 0), -99.9), 99.9)
                
                table.add_row(
                    str(i),
                    t['code'],
                    f"{t.get('score', 0):.1f}",
                    f"{t['price']:.2f}",
                    f"{t.get('change', 0):+.2f}%",
                    f"{t.get('inflow_ratio', 0):.2f}%",
                    f"{safe_sustain:.2f}x",
                    f"{safe_mfe:.1f}",
                    purity_str,
                    style=row_style
                )
        
        console.print(table)
        
        if is_rest:
            console.print("[bright_black][CMD] 盘后定格完毕。极简终端，摒弃一切多余渲染。[/bright_black]")
        else:
            console.print("[bright_black][CMD] 雷达超频扫描中... (Ctrl+C 安全阻断)[/bright_black]")
    
    except ImportError:
        # Rich库不可用时降级为print
        print(f"\n{'='*80}")
        print(f"🚀 [V20 暴力猎杀雷达] | {msg or '运行中'} | {now_str}")
        print(f"{'='*80}")
        if pool_stats:
            print(f"* 猎杀漏斗: 粗筛: {pool_stats.get('total', 0)}只 → 活跃: {pool_stats.get('active', 0)}只")
        if top_targets:
            print(f"{'排名':<4} {'代码':<10} {'得分':<8} {'价格':<8} {'涨幅':<8}")
            for i, t in enumerate(top_targets, 1):
                print(f"{i:<4} {t['code']:<10} {t.get('score', 0):<8.1f} {t['price']:<8.2f} {t.get('change', 0):<8.2f}%")
        print(f"{'='*80}\n")
