#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
半路战法模块 - V19.10 最终纯净版

核心逻辑：
- 专攻全市场股票（主板600/000 + 创业板300 + 科创板688）
- 捕捉分时均线支撑后的二次加速点
- 不做任何板块过滤，全市场通用

Author: iFlow CLI
Version: V19.10 Final
"""

from typing import Dict, List, Optional, Tuple
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class MidwayStrategy:
    """
    半路战法 - V19.10 最终纯净版
    
    核心特点：
    - 不做任何板块过滤，全市场通用
    - 涨幅区间：3% - 8.5%（半路区间）
    - 均线支撑：价格必须站稳分时均价线
    """

    def __init__(self, data_manager=None):
        """
        初始化半路战法分析器

        Args:
            data_manager: 数据管理器（可选）
        """
        self.data_manager = data_manager
        logger.info("🚀 [半路战法] V19.10 最终纯净版初始化完成")

    def check_breakout(self, stock_code: str, real_data: Dict) -> Tuple[bool, str]:
        """
        半路战法核心逻辑 - V19.10 最终纯净版
        不做任何板块过滤，全市场通用
        
        Args:
            stock_code: 股票代码
            real_data: 实时数据字典（来自easyquotation）
        
        Returns:
            Tuple[bool, str]: (是否命中, 原因)
        """
        try:
            # 1. 基础数据解包
            # 兼容两种数据格式：easyquotation原始格式和DataSourceManager转换格式
            name = real_data.get('name', '未知')
            
            # 优先使用'now'字段（easyquotation原始格式），否则使用'price'字段（DataSourceManager转换格式）
            current_price = float(real_data.get('now', 0) or real_data.get('price', 0))
            last_close = float(real_data.get('close', 0))  # 昨日收盘
            open_price = float(real_data.get('open', 0))
            
            if current_price == 0 or last_close == 0:
                return False, "数据错误"
            
            # 2. 计算涨幅
            pct_chg = (current_price - last_close) / last_close
            
            # 3. 动态阈值判断 (核心修复)
            # 这里的逻辑是：不论是主板还是创业板，半路都在 3% - 8.5% 之间抓
            # 涨太多(>9%)就是打板了，涨太少(<3%)没动能
            if not (0.03 <= pct_chg <= 0.085):
                # 只有这里返回 False，其他只要符合就放行
                return False, f"涨幅{pct_chg*100:.1f}%不在半路区间(3%-8.5%)"
            
            # 4. 均线支撑逻辑 (防止诱多)
            # 简易计算分时均价 (Approx VWAP)
            high = float(real_data.get('high', 0))
            low = float(real_data.get('low', 0))
            approx_vwap = (high + low + current_price) / 3
            
            if current_price < approx_vwap:
                return False, "价格在均线下方(弱势)"
            
            # 5. 量能逻辑 (可选，极速模式下可以先不看量，或者只看换手)
            # 如果你有成交量数据，可以加在这里
            
            return True, f"半路点火: {name} 涨幅{pct_chg*100:.1f}% 站稳均线"
        
        except Exception as e:
            logger.error(f"半路策略报错 {stock_code}: {e}")
            return False, f"Error: {e}"

    def scan_market(self, stock_list: List[str], data_manager=None) -> List[Dict]:
        """
        扫描全市场股票
        
        Args:
            stock_list: 股票代码列表
            data_manager: 数据管理器（可选）
        
        Returns:
            List[Dict]: 符合条件的股票列表
        """
        logger.info(f"🚀 [半路战法] 开始扫描全市场股票，数量: {len(stock_list)}")
        
        if data_manager is None:
            data_manager = self.data_manager
        
        if data_manager is None:
            logger.error("❌ [半路战法] 数据管理器未初始化")
            return []
        
        # 使用极速接口获取实时数据
        try:
            real_data_map = data_manager.get_realtime_price_fast(stock_list)
        except Exception as e:
            logger.error(f"❌ [半路战法] 获取实时数据失败: {e}")
            return []
        
        if not real_data_map:
            logger.error("❌ [半路战法] 获取实时数据失败，返回空")
            return []
        
        logger.info(f"✅ [半路战法] 获取实时数据成功，数量: {len(real_data_map)}")
        
        # 逐个分析股票
        results = []
        for code in stock_list:
            if code in real_data_map:
                data = real_data_map[code]
                is_hit, reason = self.check_breakout(code, data)
                
                if is_hit:
                    results.append({
                        'code': code,
                        'name': data.get('name', ''),
                        'price': data.get('now', 0),
                        'pct_chg': (float(data.get('now', 0)) - float(data.get('close', 0))) / float(data.get('close', 1)),
                        'reason': reason
                    })
        
        logger.info(f"🎉 [半路战法] 扫描结束，共发现 {len(results)} 只标的")
        
        return results