"""
资金流向分析工具
支持东方财富 API 资金流向分析
提供正确的资金分类和解读
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
from logic.fund_flow_cache import get_fund_flow_cache
from logic.logger import get_logger

logger = get_logger(__name__)


class FundFlowAnalyzer:
    """资金流向分析器（支持缓存）"""

    def __init__(self, enable_cache: bool = True):
        """
        初始化资金流向分析器
        
        Args:
            enable_cache: 是否启用缓存，默认 True
        """
        self.base_url = "http://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
        self.cache = {}  # 简单缓存（内存缓存）
        self.enable_cache = enable_cache
        
        if enable_cache:
            self.db_cache = get_fund_flow_cache()
            logger.info("✅ FundFlowAnalyzer 缓存已启用")
        else:
            self.db_cache = None
            logger.info("⚠️  FundFlowAnalyzer 缓存未启用")

    def parse_stock_code(self, stock_code: str) -> str:
        """
        解析股票代码为东方财富格式

        Args:
            stock_code: 股票代码，支持多种格式
                - '000001' → '0.000001'
                - '000001.SZ' → '0.000001'
                - '600000' → '1.600000'
                - '600000.SH' → '1.600000'

        Returns:
            东方财富格式的股票代码（如 '0.000001'）
        """
        # 移除后缀
        code = stock_code.replace('.SZ', '').replace('.SH', '').replace('.sz', '').replace('.sh', '')

        # 判断市场
        if code.startswith('6') or code.startswith('5'):
            # 上交所
            return f"1.{code}"
        else:
            # 深交所
            return f"0.{code}"

    def _get_fund_flow_from_eastmoney(self, stock_code: str, days: int = 5) -> Dict:
        """
        从东方财富 API 获取资金流向数据（私有方法）

        Args:
            stock_code: 股票代码
            days: 获取最近几天的数据

        Returns:
            资金流向数据字典
        """
        try:
            secid = self.parse_stock_code(stock_code)

            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f7",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
                "klt": "101",  # 日线
                "lmt": days
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'data' not in data or 'klines' not in data['data']:
                return {"error": "未获取到数据", "stock_code": stock_code}

            # 解析数据
            klines = data['data']['klines']
            records = []

            for kline in klines:
                parts = kline.split(',')
                records.append({
                    "date": parts[0],
                    # 注意：f51-f55 的真实含义
                    "main_net_inflow": float(parts[1]),  # 散户资金（中单+小单）
                    "super_large_net": float(parts[2]),  # 超大单净流入（机构）
                    "large_net": float(parts[3]),        # 大单净流入（游资）
                    "medium_net": float(parts[4]),       # 中单净流入
                    "small_net": float(parts[5]),        # 小单净流入
                })

            return {
                "stock_code": stock_code,
                "records": records,
                "latest": records[0] if records else None
            }

        except Exception as e:
            return {"error": str(e), "stock_code": stock_code}
    
    def get_fund_flow_cached(self, stock_code: str, days: int = 5) -> Dict:
        """
        获取资金流向数据（显式缓存版本）
        
        优先使用 SQLite 缓存，未命中则调用东方财富 API 并回写缓存。
        
        Args:
            stock_code: 股票代码
            days: 获取最近几天的数据
            
        Returns:
            资金流向数据字典
        """
        # 确保是6位代码
        stock_code_6 = stock_code.replace('.SZ', '').replace('.SH', '').replace('.sz', '').replace('.sh', '')
        
        # 1) 先查 SQLite 缓存
        if self.enable_cache and self.db_cache:
            today = datetime.now().strftime('%Y-%m-%d')
            cached_data = self.db_cache.get(stock_code_6, today)
            
            if cached_data:
                # 缓存命中，返回数据（转换为原始格式）
                logger.debug(f"✅ 缓存命中: {stock_code_6}")
                return {
                    "stock_code": stock_code,
                    "records": [cached_data],
                    "latest": cached_data,
                    "from_cache": True
                }
        
        # 2) 调用东方财富 API
        data = self._get_fund_flow_from_eastmoney(stock_code, days)
        
        # 3) 写回 SQLite 缓存
        if self.enable_cache and self.db_cache and "error" not in data:
            latest = data.get('latest')
            if latest:
                self.db_cache.save(stock_code_6, latest.get('date', ''), data)
                logger.debug(f"✅ 缓存写入: {stock_code_6}")
        
        return data
    
    def get_fund_flow(self, stock_code: str, days: int = 5) -> Dict:
        """
        获取资金流向数据（自动使用缓存）
        
        这是默认方法，会自动使用缓存（如果启用）。
        
        Args:
            stock_code: 股票代码
            days: 获取最近几天的数据
            
        Returns:
            资金流向数据字典
        """
        if self.enable_cache:
            return self.get_fund_flow_cached(stock_code, days)
        else:
            return self._get_fund_flow_from_eastmoney(stock_code, days)

    def analyze_fund_flow(self, stock_code: str) -> Dict:
        """
        分析资金流向并给出操作建议

        Args:
            stock_code: 股票代码

        Returns:
            分析结果
        """
        # 获取资金流向数据
        data = self.get_fund_flow(stock_code, days=1)

        if "error" in data:
            return {
                "stock_code": stock_code,
                "error": data["error"],
                "decision": "UNKNOWN",
                "risk_level": "UNKNOWN"
            }

        latest = data["latest"]

        # 提取关键数据
        super_large_net = latest["super_large_net"]  # 超大单（机构）
        large_net = latest["large_net"]              # 大单（游资）
        medium_net = latest["medium_net"]            # 中单
        small_net = latest["small_net"]              # 小单

        # 计算机构资金（超大单 + 大单）
        institution_net = super_large_net + large_net

        # 计算散户资金（中单 + 小单）
        retail_net = medium_net + small_net

        # 判断机构态度
        if institution_net > 0:
            institution_signal = "BUY"
        else:
            institution_signal = "SELL"

        # 判断散户态度
        if retail_net > 0:
            retail_signal = "BUY"
        else:
            retail_signal = "SELL"

        # 关键判断：对立关系
        if institution_signal == "SELL" and retail_signal == "BUY":
            # 机构卖 + 散户买 = 接盘信号 🔴
            decision = "AVOID"
            risk_level = "VERY_HIGH"
            reason = "机构在减仓，散户在接盘（典型接盘信号）"

        elif institution_signal == "BUY" and retail_signal == "SELL":
            # 机构买 + 散户卖 = 底部机会 🟢
            decision = "BUY"
            risk_level = "LOW"
            reason = "机构在吸筹，散户在逃离（底部机会）"

        elif institution_signal == "BUY" and retail_signal == "BUY":
            # 机构买 + 散户买 = 一致看多 🟡
            decision = "OBSERVE"
            risk_level = "MEDIUM"
            reason = "机构和散户一致看多，需注意追高风险"

        else:
            # 机构卖 + 散户卖 = 一致看空 🟡
            decision = "OBSERVE"
            risk_level = "MEDIUM"
            reason = "机构和散户一致看空，等待企稳"

        return {
            "stock_code": stock_code,
            "date": latest["date"],
            "fund_flow": {
                "super_large_net": super_large_net,
                "large_net": large_net,
                "medium_net": medium_net,
                "small_net": small_net,
                "institution_net": institution_net,
                "retail_net": retail_net,
            },
            "signals": {
                "institution_signal": institution_signal,
                "retail_signal": retail_signal,
            },
            "decision": decision,
            "risk_level": risk_level,
            "reason": reason,
            "data_source": "EASTMONEY_REALTIME"
        }

    def format_analysis(self, result: Dict) -> str:
        """
        格式化分析结果为可读文本

        Args:
            result: analyze_fund_flow 的返回结果

        Returns:
            格式化的分析报告
        """
        if "error" in result:
            return f"❌ 错误：{result['error']}"

        fund_flow = result["fund_flow"]

        report = f"""
## 资金流向分析

**股票代码**: {result['stock_code']}
**日期**: {result['date']}
**数据来源**: {result['data_source']}

### 资金流向详情
- 超大单净流入: {fund_flow['super_large_net'] / 10000:.2f} 万元
- 大单净流入: {fund_flow['large_net'] / 10000:.2f} 万元
- 中单净流入: {fund_flow['medium_net'] / 10000:.2f} 万元
- 小单净流入: {fund_flow['small_net'] / 10000:.2f} 万元

### 关键判断
- 机构资金（超大单+大单）: {fund_flow['institution_net'] / 10000:.2f} 万元
- 散户资金（中单+小单）: {fund_flow['retail_net'] / 10000:.2f} 万元

### 信号解读
- 机构态度: {"买入 ✅" if result['signals']['institution_signal'] == 'BUY' else "卖出 ❌"}
- 散户态度: {"买入 ✅" if result['signals']['retail_signal'] == 'BUY' else "卖出 ❌"}

### 操作建议
**风险等级**: {self._get_risk_emoji(result['risk_level'])} {result['risk_level']}
**操作建议**: {self._get_decision_emoji(result['decision'])} {result['decision']}
**理由**: {result['reason']}
"""

        return report

    def _get_risk_emoji(self, risk_level: str) -> str:
        """获取风险等级表情"""
        emoji_map = {
            "VERY_HIGH": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
            "UNKNOWN": "⚪"
        }
        return emoji_map.get(risk_level, "⚪")

    def _get_decision_emoji(self, decision: str) -> str:
        """获取决策表情"""
        emoji_map = {
            "BUY": "🟢",
            "SELL": "🔴",
            "AVOID": "⛔",
            "OBSERVE": "👁️",
            "UNKNOWN": "❓"
        }
        return emoji_map.get(decision, "❓")


# 全局实例
_fund_flow_analyzer = FundFlowAnalyzer()


def analyze_fund_flow(stock_code: str) -> Dict:
    """
    便捷函数：分析股票资金流向

    Args:
        stock_code: 股票代码

    Returns:
        分析结果
    """
    return _fund_flow_analyzer.analyze_fund_flow(stock_code)


def format_fund_flow_analysis(stock_code: str) -> str:
    """
    便捷函数：获取格式化的资金流向分析报告

    Args:
        stock_code: 股票代码

    Returns:
        格式化的分析报告
    """
    result = analyze_fund_flow(stock_code)
    return _fund_flow_analyzer.format_analysis(result)


if __name__ == "__main__":
    # 测试
    import sys

    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
    else:
        stock_code = "300997"  # 欢乐家

    print(format_fund_flow_analysis(stock_code))