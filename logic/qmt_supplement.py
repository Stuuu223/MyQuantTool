"""
QMT 数据补充模块
补充现有 enhanced_stock_analyzer.py 缺失的功能：
1. 换手率（turnover_rate）
2. Tick成交验证（验证成交额单位）
3. 分时均线（1分钟/5分钟K线）
4. 盘口数据（买卖盘前5档）
5. 分时形态识别

最后更新: 2026-02-03
版本: 1.0
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import os
import requests

logger = logging.getLogger(__name__)


class QMTSupplement:
    """QMT 数据补充类"""

    def __init__(self):
        """初始化补充模块"""
        self.xtdata = None
        self.converter = None
        self._init_qmt()
        # 禁用系统代理，避免 AkShare API 调用失败
        self._disable_proxy()

    def _disable_proxy(self):
        """禁用系统代理"""
        # 禁用环境变量代理
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        os.environ.pop('http_proxy', None)
        os.environ.pop('https_proxy', None)
        os.environ.pop('ALL_PROXY', None)
        os.environ.pop('all_proxy', None)
        logger.info("已禁用系统代理设置")

    def _get_safe_session(self) -> requests.Session:
        """获取禁用代理的 requests Session"""
        session = requests.Session()
        session.trust_env = False  # 禁用环境变量和系统代理
        return session

    def _init_qmt(self):
        """初始化 QMT 连接"""
        try:
            from xtquant import xtdata
            from logic.utils.code_converter import CodeConverter
            self.xtdata = xtdata
            self.converter = CodeConverter()
            logger.info("QMT 补充模块初始化成功")
        except ImportError as e:
            logger.warning(f"无法导入 QMT 模块: {e}")

    def is_available(self) -> bool:
        """检查 QMT 是否可用"""
        return self.xtdata is not None

    # ========== 1. 换手率 ==========

    def get_turnover_rate(self, stock_code: str, days: int = 1) -> Optional[List[Dict[str, Any]]]:
        """
        获取换手率

        Args:
            stock_code: 股票代码（如 '300997'）
            days: 获取最近几天的数据（默认1天）

        Returns:
            换手率数据列表，每条记录包含：
            - date: 日期
            - turnover_rate: 换手率（%）
            - level: 活跃度（极度活跃/活跃/正常/低迷）

        用途:
        - >20%: 极度活跃（游资可能）
        - 10-20%: 活跃
        - 5-10%: 正常
        - <5%: 低迷
        """
        # 使用 AkShare stock_zh_a_daily 获取换手率数据
        try:
            import akshare as ak
            
            # stock_zh_a_daily 需要带市场前缀的股票代码
            if stock_code.startswith('6'):
                symbol = f"sh{stock_code}"
            else:
                symbol = f"sz{stock_code}"
            
            # 获取历史数据（stock_zh_a_daily 不需要日期范围参数，返回所有数据）
            df = ak.stock_zh_a_daily(symbol=symbol)
            
            if df is None or df.empty:
                logger.warning(f"AkShare 未找到 {stock_code} 的数据")
                return None
            
            # 转换日期格式并排序
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 取最近几天
            df = df.tail(days)
            
            # 重命名列（turnover 是小数形式，需要乘以 100 得到百分比）
            df = df.rename(columns={'turnover': 'turnover_rate'})
            df['turnover_rate'] = df['turnover_rate'] * 100  # 转换为百分比
            df = df[['date', 'turnover_rate']]
            
            # 构建返回结果
            result = []
            for _, row in df.iterrows():
                rate = row['turnover_rate']
                if pd.isna(rate):
                    continue
                
                # 活跃度判断
                if rate > 20:
                    level = "极度活跃"
                elif rate > 10:
                    level = "活跃"
                elif rate > 5:
                    level = "正常"
                else:
                    level = "低迷"
                
                result.append({
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'turnover_rate': round(rate, 2),
                    'level': level
                })
            
            return result if result else None
            
        except Exception as e:
            logger.error(f"获取换手率失败: {e}")
            return None

    # ========== 2. Tick成交验证 ==========

    def validate_volume_amount(self, stock_code: str, date: str = None) -> Dict[str, Any]:
        """
        验证成交量/成交额单位（使用 AkShare 历史数据）

        Args:
            stock_code: 股票代码
            date: 日期（YYYYMMDD 格式，None 为今日）

        Returns:
            验证结果字典：
            {
                "is_valid": True/False,
                "volume_unit": "手" | "股",
                "amount_unit": "元" | "万元",
                "error_ratio": 0.02,
                "理论成交额(元)": 881827,
                "实际成交额": 8818.77,
                "异常说明": "成交额单位是万元，需要除以10000"
            }

        用途:
        解决今天 300997 成交额单位不明的问题
        """
        try:
            import akshare as ak
            
            # 转换代码格式
            if stock_code.startswith('6'):
                symbol = f"sh{stock_code}"
            else:
                symbol = f"sz{stock_code}"
            
            # 使用 stock_zh_a_daily 获取历史数据
            df = ak.stock_zh_a_daily(symbol=symbol)
            
            if df is None or df.empty:
                return {"error": f"AkShare 未找到 {stock_code} 的数据"}
            
            # 转换日期格式并排序
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 如果指定了日期，查找对应日期的数据
            if date is not None:
                date_obj = pd.to_datetime(date, format='%Y%m%d')
                date_df = df[df['date'] == date_obj]
                if date_df.empty:
                    return {"error": f"AkShare 未找到 {stock_code} 在 {date} 的数据"}
                row = date_df.iloc[0]
            else:
                # 获取最近一天的数据
                row = df.iloc[-1]
            
            # 提取数据（stock_zh_a_daily 的列名是英文）
            close = row['close']           # 元
            volume = row['volume']         # 股（不是手！）
            amount = row['amount']         # 元
            
            # stock_zh_a_daily 的成交量单位是"股"，不是"手"
            # 1手 = 100股
            volume_hands = volume / 100
            
            # 计算理论成交额
            theoretical_amount = volume * close
            
            # 验证逻辑
            error_ratio = abs(theoretical_amount - amount) / theoretical_amount if theoretical_amount > 0 else 0
            
            result = {
                "is_valid": bool(error_ratio < 0.05),  # 转换为 Python bool
                "volume_unit": "股",
                "error_ratio": float(round(error_ratio, 4)),  # 转换为 Python float
                "理论成交额(元)": float(round(theoretical_amount, 2)),
                "实际成交额": float(round(amount, 2)),
                "成交量(股)": float(volume),
                "成交量(手)": float(volume_hands)
            }
            
            # 判断单位
            if error_ratio < 0.05:
                result["amount_unit"] = "元"
                result["异常说明"] = "成交额单位正常"
            else:
                # 检查是否是万元
                error_ratio_wan = abs(theoretical_amount / 10000 - amount) / (theoretical_amount / 10000) if theoretical_amount > 0 else 0
                if error_ratio_wan < 0.05:
                    result["amount_unit"] = "万元"
                    result["is_valid"] = True
                    result["异常说明"] = "成交额单位是万元，需要除以10000"
                    result["实际成交额(元)"] = float(round(amount * 10000, 2))
                else:
                    result["amount_unit"] = "未知"
                    result["异常说明"] = f"成交额单位无法确定，误差率 {error_ratio:.2%}"
            
            return result
            
        except Exception as e:
            logger.error(f"验证成交额失败: {e}")
            return {"error": str(e)}

    # ========== 3. 分时均线 ==========

    def get_intraday_ma(self, stock_code: str, period: str = '1m', ma_windows: List[int] = [5, 10, 20]) -> Dict[str, Any]:
        """
        获取分时均线（优先使用 QMT，失败时返回空数据）

        注意：AkShare 的分时接口（stock_zh_a_hist_min_em）当前不可用
        该功能主要依赖 QMT 实时数据，仅在交易时间可用

        Args:
            stock_code: 股票代码
            period: 周期，'1m' 或 '5m'
            ma_windows: MA周期列表

        Returns:
            {
                "period": "1m",
                "times": ["09:31", "09:32", ...],
                "prices": [24.10, 24.15, ...],
                "ma5": [24.08, 24.12, ...],
                "ma10": [24.05, 24.10, ...],
                "ma20": [24.02, 24.08, ...],
                "pattern": "冲高回落" | "V型反转" | "震荡盘整" | "正常波动"
            }
        """
        # 优先使用 QMT 获取实时分时数据
        if self.is_available() and self.xtdata is not None:
            try:
                # 转换为 QMT 代码格式
                qmt_code = self.converter.to_qmt(stock_code)
                
                # 获取当日分时数据
                data = self.xtdata.get_market_data(
                    field_list=['time', 'lastPrice'],
                    stock_list=[qmt_code],
                    period=period,
                    start_time='',
                    end_time='',
                    count=-1,
                    dividend_type='front'
                )
                
                if data and qmt_code in data:
                    prices = data[qmt_code]['lastPrice']
                    times = data[qmt_code]['time']
                    
                    # 过滤空值
                    valid_indices = [i for i, p in enumerate(prices) if p is not None and p > 0]
                    if not valid_indices:
                        return {"error": "今日没有分时数据（休盘时间或数据不可用）"}
                    
                    prices = [float(prices[i]) for i in valid_indices]
                    times = [times[i] for i in valid_indices]
                    
                    # 计算MA
                    result = {
                        "period": period,
                        "date": datetime.now().strftime('%Y-%m-%d'),
                        "times": [t.strftime('%H:%M') if hasattr(t, 'strftime') else str(t) for t in times],
                        "prices": prices
                    }
                    
                    for w in ma_windows:
                        if len(prices) >= w:
                            ma_values = pd.Series(prices).rolling(window=w).mean().tolist()
                            result[f"ma{w}"] = [round(float(v), 2) if not pd.isna(v) else None for v in ma_values]
                        else:
                            result[f"ma{w}"] = []
                    
                    # 识别形态
                    result["pattern"] = self._identify_intraday_pattern(prices)
                    
                    return result
                else:
                    return {"error": "QMT 未返回分时数据（可能是休盘时间）"}
            except Exception as e:
                logger.warning(f"QMT 获取分时数据失败: {e}")
        
        # AkShare 分时接口当前不可用（push2his.eastmoney.com 连接问题）
        # 返回提示信息
        return {
            "error": "分时数据当前不可用（需在交易时间使用 QMT 客户端获取）",
            "suggestion": "请使用 Enhanced 模式进行分析，该模式包含资金流向和诱多检测功能"
        }

    def _identify_intraday_pattern(self, prices: List[float]) -> str:
        """
        识别分时走势形态

        Args:
            prices: 价格列表

        Returns:
            形态描述
        """
        if len(prices) < 120:
            return "数据不足"

        # 分割早盘和午盘
        # 假设数据是按时间顺序的，前120分钟是早盘，后面是午盘
        morning = prices[:min(120, len(prices) // 2)]
        afternoon = prices[len(prices) // 2:]

        if len(morning) < 2 or len(afternoon) < 2:
            return "数据不足"

        # 计算趋势
        morning_trend = (morning[-1] - morning[0]) / morning[0] if morning[0] != 0 else 0
        afternoon_trend = (afternoon[-1] - afternoon[0]) / afternoon[0] if afternoon[0] != 0 else 0

        # 判断形态
        if morning_trend > 0.03 and afternoon_trend < -0.02:
            return "冲高回落"
        elif morning_trend < -0.02 and afternoon_trend > 0.03:
            return "V型反转"
        elif abs(morning_trend) < 0.01 and abs(afternoon_trend) < 0.01:
            return "震荡盘整"
        elif morning_trend > 0.02 and afternoon_trend > 0.01:
            return "单边上涨"
        elif morning_trend < -0.02 and afternoon_trend < -0.01:
            return "单边下跌"
        else:
            return "正常波动"

    # ========== 4. 盘口数据 ==========

    def get_order_book(self, stock_code: str) -> Dict[str, Any]:
        """
        获取盘口数据（买卖盘前5档）

        Args:
            stock_code: 股票代码

        Returns:
            {
                "bid": [
                    {"price": 24.28, "volume": 0.42},
                    {"price": 24.27, "volume": 1.20},
                    ...
                ],
                "ask": [
                    {"price": 24.29, "volume": 0.48},
                    {"price": 24.30, "volume": 0.85},
                    ...
                ],
                "bid_ask_imbalance": -0.6,
                "pressure": "卖盘压力大"
            }

        用途:
        - 买盘 > 卖盘: 买盘强势
        - 卖盘 > 买盘: 卖盘压力大
        - 买卖均衡: 观望
        """
        if not self.is_available():
            return {"error": "QMT 不可用"}

        try:
            # 转换代码格式
            qmt_code = self.converter.to_qmt(stock_code)

            # 获取Tick数据
            tick_data = self.xtdata.get_full_tick([qmt_code])

            if tick_data is None or len(tick_data) == 0 or qmt_code not in tick_data:
                return {"error": "未找到Tick数据"}

            tick = tick_data[qmt_code]

            # 提取买卖盘（QMT 返回的是列表格式）
            bid_prices = tick.get('bidPrice', [])
            ask_prices = tick.get('askPrice', [])
            bid_vols = tick.get('bidVol', [])
            ask_vols = tick.get('askVol', [])

            bid = []
            ask = []

            for i in range(min(5, len(bid_prices))):
                if bid_prices[i] > 0:
                    bid.append({
                        "price": round(bid_prices[i], 2),
                        "volume": round(bid_vols[i], 2) if i < len(bid_vols) else 0
                    })

            for i in range(min(5, len(ask_prices))):
                if ask_prices[i] > 0:
                    ask.append({
                        "price": round(ask_prices[i], 2),
                        "volume": round(ask_vols[i], 2) if i < len(ask_vols) else 0
                    })

            # 计算买卖盘不平衡度
            bid_total = sum([b['volume'] for b in bid])
            ask_total = sum([a['volume'] for a in ask])

            imbalance = 0
            pressure = "无数据"

            if bid_total + ask_total > 0:
                imbalance = (bid_total - ask_total) / (bid_total + ask_total)
                if imbalance > 0.3:
                    pressure = "买盘强势"
                elif imbalance < -0.3:
                    pressure = "卖盘压力大"
                else:
                    pressure = "买卖均衡"

            return {
                "bid": bid,
                "ask": ask,
                "bid_total": round(bid_total, 2),
                "ask_total": round(ask_total, 2),
                "bid_ask_imbalance": round(imbalance, 2),
                "pressure": pressure
            }

        except Exception as e:
            logger.error(f"获取盘口数据失败: {e}")
            return {"error": str(e)}

    # ========== 5. 综合补充 ==========

    def get_supplement_data(self, stock_code: str, days: int = 1) -> Dict[str, Any]:
        """
        获取所有补充数据

        Args:
            stock_code: 股票代码
            days: 换手率数据天数

        Returns:
            {
                "turnover_rate": [...],
                "tick_validation": {...},
                "intraday_ma_1m": {...},
                "intraday_ma_5m": {...},
                "order_book": {...}
            }
        """
        result = {
            "stock_code": stock_code,
            "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "turnover_rate": None,
            "tick_validation": None,
            "intraday_ma_1m": None,
            "intraday_ma_5m": None,
            "order_book": None
        }

        # 换手率
        result["turnover_rate"] = self.get_turnover_rate(stock_code, days)

        # Tick成交验证
        result["tick_validation"] = self.validate_volume_amount(stock_code)

        # 分时均线
        result["intraday_ma_1m"] = self.get_intraday_ma(stock_code, '1m')
        result["intraday_ma_5m"] = self.get_intraday_ma(stock_code, '5m')

        # 盘口数据
        result["order_book"] = self.get_order_book(stock_code)

        return result


# ========== 便捷函数 ==========

def get_qmt_supplement(stock_code: str, days: int = 1) -> Dict[str, Any]:
    """
    获取 QMT 补充数据（便捷函数）

    Args:
        stock_code: 股票代码
        days: 换手率数据天数

    Returns:
        补充数据字典

    Examples:
        >>> data = get_qmt_supplement('300997')
        >>> print(data['tick_validation'])
        >>> print(data['intraday_ma_1m']['pattern'])
    """
    supplement = QMTSupplement()
    return supplement.get_supplement_data(stock_code, days)


def validate_stock_amount(stock_code: str, date: str = None) -> Dict[str, Any]:
    """
    验证股票成交额单位（便捷函数）

    Args:
        stock_code: 股票代码
        date: 日期

    Returns:
        验证结果

    Examples:
        >>> result = validate_stock_amount('300997', '20260202')
        >>> if not result['is_valid']:
        ...     print(f"异常: {result['异常说明']}")
    """
    supplement = QMTSupplement()
    return supplement.validate_volume_amount(stock_code, date)


def get_intraday_pattern(stock_code: str) -> str:
    """
    获取分时走势形态（便捷函数）

    Args:
        stock_code: 股票代码

    Returns:
        形态描述

    Examples:
        >>> pattern = get_intraday_pattern('300997')
        >>> if pattern == "冲高回落":
        ...     print("注意诱多风险")
    """
    supplement = QMTSupplement()
    data = supplement.get_intraday_ma(stock_code)
    if 'error' in data:
        return data['error']
    return data.get('pattern', '未知')


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
    else:
        stock_code = "300997"

    print("=" * 80)
    print(f"QMT 补充数据测试 - {stock_code}")
    print("=" * 80)

    supplement = QMTSupplement()

    if not supplement.is_available():
        print("❌ QMT 不可用")
        sys.exit(1)

    # 测试换手率
    print("\n1. 换手率:")
    turnover = supplement.get_turnover_rate(stock_code)
    if turnover:
        for t in turnover:
            print(f"  {t['date']}: {t['turnover_rate']}% ({t['level']})")

    # 测试Tick验证
    print("\n2. Tick成交验证:")
    validation = supplement.validate_volume_amount(stock_code)
    if 'error' not in validation:
        print(f"  是否有效: {validation['is_valid']}")
        print(f"  成交量单位: {validation['volume_unit']}")
        print(f"  成交额单位: {validation['amount_unit']}")
        print(f"  误差率: {validation['error_ratio']:.2%}")
        print(f"  说明: {validation.get('异常说明', '')}")

    # 测试分时均线
    print("\n3. 分时均线:")
    intraday = supplement.get_intraday_ma(stock_code)
    if 'error' not in intraday:
        print(f"  周期: {intraday['period']}")
        print(f"  形态: {intraday['pattern']}")
        print(f"  数据点: {len(intraday['prices'])}")

    # 测试盘口
    print("\n4. 盘口数据:")
    order_book = supplement.get_order_book(stock_code)
    if 'error' not in order_book:
        print(f"  买卖压力: {order_book['pressure']}")
        print(f"  不平衡度: {order_book['bid_ask_imbalance']}")
        if order_book['bid']:
            print(f"  买1: {order_book['bid'][0]['price']} ({order_book['bid'][0]['volume']}手)")
        if order_book['ask']:
            print(f"  卖1: {order_book['ask'][0]['price']} ({order_book['ask'][0]['volume']}手)")

    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)