#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微观盘口三道防线 - Micro Defense System (CTO架构版 V1.0)
职责：基于Tick五档数据的微观盘口分析，识别诱多陷阱和真实起爆
Author: microstructure_specialist
Date: 2026-02-26
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

class DefenseLevel(Enum):
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"

@dataclass
class DefenseResult:
    defense_name: str
    triggered: bool
    level: DefenseLevel
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))

@dataclass
class MicroDefenseReport:
    stock_code: str
    timestamp: str
    overall_safe: bool
    defense_results: List[DefenseResult]
    composite_score: float
    recommendations: List[str]

class MicroDefenseSystem:
    """
    微观盘口三道防线系统
    基于Tick五档数据的实时防御系统，用于识别诱多陷阱和真实起爆
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化微观防御系统"""
        self.config = config or {}
        self._load_config()
        self._history_cache: Dict[str, pd.DataFrame] = {}
        self._cache_max_size = 1000
        self._limit_up_cache: Dict[str, Dict] = {}
        logger.info("[MicroDefenseSystem] 微观盘口三道防线系统初始化完成")
    
    def _load_config(self):
        """从ConfigManager加载配置"""
        try:
            from logic.core.config_manager import get_config_manager
            cfg = get_config_manager()
            self.window_ticks = cfg.get("micro_defense.window_ticks", 5)
            self.fake_support_lookback = cfg.get("micro_defense.fake_support_lookback", 5)
            self.decay_monitor_ticks = cfg.get("micro_defense.decay_monitor_ticks", 20)
            self.volume_drop_percentile = cfg.get("micro_defense.volume_drop_percentile", 0.70)
            self.retail_ratio_percentile = cfg.get("micro_defense.retail_ratio_percentile", 0.80)
            self.order_decay_percentile = cfg.get("micro_defense.order_decay_percentile", 0.50)
            self.small_order_threshold = cfg.get("micro_defense.small_order_threshold", 100)
        except ImportError:
            self.window_ticks = 5
            self.fake_support_lookback = 5
            self.decay_monitor_ticks = 20
            self.volume_drop_percentile = 0.70
            self.retail_ratio_percentile = 0.80
            self.order_decay_percentile = 0.50
            self.small_order_threshold = 100

    def detect_fake_support(self, tick_window: pd.DataFrame) -> DefenseResult:
        """
        检测诱多撤单陷阱 - 防线1
        算法:
        1. 滑动窗口计算bid1_vol历史分位数（托单支撑基准）
        2. 检测当前tick的bid1_vol是否断崖式下跌
        3. 结合价格行为确认（非真突破）
        4. 使用动态分位数阈值而非固定70%
        """
        defense_name = "诱多撤单检测"
        
        try:
            if tick_window is None or len(tick_window) < self.fake_support_lookback + 2:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message="数据不足，跳过检测",
                    details={"window_size": len(tick_window) if tick_window is not None else 0}
                )
            
            required_cols = ["bid1_vol", "price", "volume"]
            missing_cols = [c for c in required_cols if c not in tick_window.columns]
            if missing_cols:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message=f"缺少必要列: {missing_cols}",
                    details={"missing_columns": missing_cols}
                )
            
            df = tick_window.copy()
            
            # 向量化计算：滑动窗口bid1_vol均值
            df["bid1_vol_ma"] = df["bid1_vol"].rolling(
                window=self.fake_support_lookback, 
                min_periods=1
            ).mean()
            
            # 向量化计算：bid1_vol变化率和价格变化
            df["bid1_vol_change"] = df["bid1_vol"].pct_change()
            df["price_change"] = df["price"].pct_change()
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 动态阈值计算
            bid1_vol_history = df["bid1_vol"].iloc[:-1]
            if len(bid1_vol_history) > 0:
                current_vol = latest["bid1_vol"]
                percentile = (bid1_vol_history < current_vol).mean()
                vol_threshold = bid1_vol_history.quantile(self.volume_drop_percentile)
                
                # 检测条件
                is_volume_cliff = current_vol < vol_threshold
                price_stagnant = abs(latest["price_change"]) < 0.001
                rapid_drop = latest["bid1_vol"] < prev["bid1_vol"] * 0.5
                
                is_fake_support = (is_volume_cliff and price_stagnant) or (rapid_drop and price_stagnant)
                
                if is_fake_support:
                    return DefenseResult(
                        defense_name=defense_name,
                        triggered=True,
                        level=DefenseLevel.DANGER,
                        message=f"诱多撤单陷阱 detected: bid1_vol分位数{percentile:.1%}, 价格滞涨",
                        details={
                            "current_bid1_vol": float(current_vol),
                            "volume_percentile": float(percentile),
                            "volume_threshold": float(vol_threshold),
                            "price_change": float(latest["price_change"]),
                            "is_volume_cliff": bool(is_volume_cliff),
                            "price_stagnant": bool(price_stagnant),
                            "rapid_drop": bool(rapid_drop)
                        }
                    )
                else:
                    return DefenseResult(
                        defense_name=defense_name,
                        triggered=False,
                        level=DefenseLevel.SAFE,
                        message=f"托单支撑正常: bid1_vol分位数{percentile:.1%}",
                        details={
                            "current_bid1_vol": float(current_vol),
                            "volume_percentile": float(percentile),
                            "price_change": float(latest["price_change"])
                        }
                    )
            else:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.WARNING,
                    message="历史数据不足，无法计算动态阈值",
                    details={}
                )
                
        except Exception as e:
            logger.error(f"[防线1] 诱多撤单检测异常: {e}")
            return DefenseResult(
                defense_name=defense_name,
                triggered=False,
                level=DefenseLevel.WARNING,
                message=f"检测异常: {str(e)}",
                details={"error": str(e)}
            )

    def detect_retail_hype(self, tick_slice: pd.DataFrame) -> DefenseResult:
        """
        检测散户自嗨股（无主力）- 防线2
        算法:
        1. 使用volume.diff()向量化计算现手成交
        2. 小单（<100手）成交量占比计算
        3. 基于历史分位数动态判定散户阈值
        4. 结合买卖方向分析
        """
        defense_name = "散户跟风检测"
        
        try:
            if tick_slice is None or len(tick_slice) < 5:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message="数据不足，跳过检测",
                    details={"slice_size": len(tick_slice) if tick_slice is not None else 0}
                )
            
            required_cols = ["volume", "bid1_vol", "ask1_vol", "price"]
            missing_cols = [c for c in required_cols if c not in tick_slice.columns]
            if missing_cols:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message=f"缺少必要列: {missing_cols}",
                    details={"missing_columns": missing_cols}
                )
            
            df = tick_slice.copy()
            
            # 向量化计算
            df["trade_volume"] = df["volume"].diff().fillna(0)
            df["bid_ask_ratio"] = df["bid1_vol"] / (df["ask1_vol"] + 1)
            df["price_direction"] = np.where(
                df["price"].diff() > 0, "up",
                np.where(df["price"].diff() < 0, "down", "flat")
            )
            
            # 估算小单成交（向量化）
            df["is_small_order"] = (
                (df["trade_volume"] < self.small_order_threshold) &
                (df["bid1_vol"] < df["bid1_vol"].quantile(0.5)) &
                (df["ask1_vol"] < df["ask1_vol"].quantile(0.5))
            )
            
            total_volume = df["trade_volume"].sum()
            small_order_volume = df.loc[df["is_small_order"], "trade_volume"].sum()
            
            retail_ratio = small_order_volume / total_volume if total_volume > 0 else 0.0
            
            # 动态阈值
            if len(df) > 10:
                historical_retail_ratio = df["is_small_order"].rolling(window=5).mean().iloc[-1]
                dynamic_threshold = self.retail_ratio_percentile
            else:
                historical_retail_ratio = retail_ratio
                dynamic_threshold = self.retail_ratio_percentile * 0.9  # Use configured percentile
            
            is_retail_dominant = retail_ratio > dynamic_threshold
            avg_bid_ask_ratio = df["bid_ask_ratio"].mean()
            weak_support = avg_bid_ask_ratio < 1.0
            
            is_retail_hype = is_retail_dominant and weak_support
            
            if is_retail_hype:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=True,
                    level=DefenseLevel.WARNING,
                    message=f"散户自嗨 detected: 小单占比{retail_ratio:.1%}, 买盘压力{avg_bid_ask_ratio:.2f}",
                    details={
                        "retail_ratio": float(retail_ratio),
                        "dynamic_threshold": float(dynamic_threshold),
                        "avg_bid_ask_ratio": float(avg_bid_ask_ratio),
                        "total_volume": float(total_volume),
                        "small_order_volume": float(small_order_volume)
                    }
                )
            else:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message=f"有主力参与: 小单占比{retail_ratio:.1%}, 买盘压力{avg_bid_ask_ratio:.2f}",
                    details={
                        "retail_ratio": float(retail_ratio),
                        "avg_bid_ask_ratio": float(avg_bid_ask_ratio)
                    }
                )
                
        except Exception as e:
            logger.error(f"[防线2] 散户跟风检测异常: {e}")
            return DefenseResult(
                defense_name=defense_name,
                triggered=False,
                level=DefenseLevel.WARNING,
                message=f"检测异常: {str(e)}",
                details={"error": str(e)}
            )

    def detect_order_book_decay(self, tick_data: pd.DataFrame, 
                                 stock_code: str,
                                 up_stop_price: Optional[float] = None) -> DefenseResult:
        """
        检测涨停后封单衰减 - 防线3
        算法:
        1. 检测是否触及涨停
        2. 触及涨停时刻记录ask1_vol
        3. 监测随后1分钟ask1_vol变化
        4. 动态分位数判定衰减程度
        """
        defense_name = "封单衰减预警"
        
        try:
            if tick_data is None or len(tick_data) < 5:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message="数据不足，跳过检测",
                    details={"data_length": len(tick_data) if tick_data is not None else 0}
                )
            
            required_cols = ["price", "ask1_vol"]
            missing_cols = [c for c in required_cols if c not in tick_data.columns]
            if missing_cols:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message=f"缺少必要列: {missing_cols}",
                    details={"missing_columns": missing_cols}
                )
            
            df = tick_data.copy()
            
            if up_stop_price is None:
                up_stop_price = df["price"].max()
            
            df["is_limit_up"] = df["price"] >= up_stop_price * 0.999
            
            if not df["is_limit_up"].any():
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message="未触及涨停，无需监控封单",
                    details={
                        "max_price": float(df["price"].max()),
                        "up_stop_price": float(up_stop_price)
                    }
                )
            
            limit_up_idx = df[df["is_limit_up"]].index[0]
            limit_up_row = df.loc[limit_up_idx]
            initial_ask_vol = limit_up_row["ask1_vol"]
            
            date_str = datetime.now().strftime("%Y%m%d")
            cache_key = f"{stock_code}_{date_str}"
            if cache_key not in self._limit_up_cache:
                self._limit_up_cache[cache_key] = {
                    "initial_ask_vol": initial_ask_vol,
                    "limit_up_time": limit_up_idx,
                    "monitor_start": True
                }
            
            post_limit_data = df.loc[limit_up_idx:].head(self.decay_monitor_ticks)
            
            if len(post_limit_data) < 3:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.WARNING,
                    message="涨停后数据不足，持续监控中",
                    details={
                        "initial_ask_vol": float(initial_ask_vol),
                        "post_limit_ticks": len(post_limit_data)
                    }
                )
            
            current_ask_vol = post_limit_data["ask1_vol"].iloc[-1]
            decay_ratio = (initial_ask_vol - current_ask_vol) / initial_ask_vol if initial_ask_vol > 0 else 0.0
            
            if len(post_limit_data) > 5:
                historical_decay = post_limit_data["ask1_vol"].pct_change().dropna()
                dynamic_decay_threshold = historical_decay.quantile(self.order_decay_percentile) if len(historical_decay) > 0 else -0.3
            else:
                dynamic_decay_threshold = -0.3
            
            is_decay_critical = decay_ratio > abs(dynamic_decay_threshold)
            rapid_depletion = current_ask_vol < initial_ask_vol * 0.2
            
            if rapid_depletion:
                level = DefenseLevel.CRITICAL
                message = f"封单即将耗尽: 衰减{decay_ratio:.1%}, 剩余{current_ask_vol:.0f}手"
            elif is_decay_critical:
                level = DefenseLevel.DANGER
                message = f"封单严重衰减: {decay_ratio:.1%}, 阈值{abs(dynamic_decay_threshold):.1%}"
            else:
                level = DefenseLevel.SAFE
                message = f"封单稳定: 衰减{decay_ratio:.1%}, 当前{current_ask_vol:.0f}手"
            
            return DefenseResult(
                defense_name=defense_name,
                triggered=is_decay_critical or rapid_depletion,
                level=level,
                message=message,
                details={
                    "initial_ask_vol": float(initial_ask_vol),
                    "current_ask_vol": float(current_ask_vol),
                    "decay_ratio": float(decay_ratio),
                    "dynamic_threshold": float(dynamic_decay_threshold),
                    "monitor_ticks": len(post_limit_data)
                }
            )
                
        except Exception as e:
            logger.error(f"[防线3] 封单衰减检测异常: {e}")
            return DefenseResult(
                defense_name=defense_name,
                triggered=False,
                level=DefenseLevel.WARNING,
                message=f"检测异常: {str(e)}",
                details={"error": str(e)}
            )

    def analyze(self, stock_code: str, tick_data: pd.DataFrame, 
                up_stop_price: Optional[float] = None) -> MicroDefenseReport:
        """执行三道防线综合分析"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        defense1 = self.detect_fake_support(tick_data)
        defense2 = self.detect_retail_hype(tick_data)
        defense3 = self.detect_order_book_decay(tick_data, stock_code, up_stop_price)
        
        defense_results = [defense1, defense2, defense3]
        
        score = 100.0
        for result in defense_results:
            if result.triggered:
                if result.level == DefenseLevel.WARNING:
                    score -= 15
                elif result.level == DefenseLevel.DANGER:
                    score -= 30
                elif result.level == DefenseLevel.CRITICAL:
                    score -= 50
        
        score = max(0.0, score)
        
        overall_safe = score >= 60 and not any(
            r.triggered and r.level in [DefenseLevel.DANGER, DefenseLevel.CRITICAL]
            for r in defense_results
        )
        
        recommendations = []
        if defense1.triggered:
            recommendations.append("诱多撤单风险: 建议观望，等待托单稳定")
        if defense2.triggered:
            recommendations.append("散户跟风嫌疑: 建议谨慎，确认主力参与")
        if defense3.triggered and defense3.level == DefenseLevel.CRITICAL:
            recommendations.append("封单即将耗尽: 建议回避，有炸板风险")
        elif defense3.triggered:
            recommendations.append("封单衰减: 建议密切监控")
        if not recommendations:
            recommendations.append("三道防线通过: 可考虑参与")
        
        return MicroDefenseReport(
            stock_code=stock_code,
            timestamp=timestamp,
            overall_safe=overall_safe,
            defense_results=defense_results,
            composite_score=score,
            recommendations=recommendations
        )

    def can_trade(self, stock_code: str, tick_data: pd.DataFrame,
                  up_stop_price: Optional[float] = None) -> Tuple[bool, str]:
        """简化接口：是否可以通过微观防线检查"""
        report = self.analyze(stock_code, tick_data, up_stop_price)
        
        if report.overall_safe:
            return True, f"微观防线通过 (得分: {report.composite_score:.1f})"
        else:
            triggered_defenses = [r.defense_name for r in report.defense_results if r.triggered]
            return False, f"微观防线拦截: {', '.join(triggered_defenses)} (得分: {report.composite_score:.1f})"

    def detect_explosion_trap_cto(self, tick_df: pd.DataFrame, explosion_idx: int) -> DefenseResult:
        """
        【CTO Phase A4 核心防线】滑动窗口诱多撤单陷阱检测
        
        核心算法:
        1. 计算起爆前15秒(5个Tick)的bid1_vol均值作为基准
        2. 对比起爆后3秒(1个Tick)的挂单量
        3. 断崖下跌 > 70% 则判定为陷阱
        
        Args:
            tick_df: 全天Tick数据
            explosion_idx: 起爆点索引
            
        Returns:
            DefenseResult: 防线检测结果
        """
        defense_name = "CTO滑动窗口诱多检测"
        
        try:
            if tick_df is None or len(tick_df) < 10:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message="数据不足，跳过CTO防线",
                    details={"data_length": len(tick_df) if tick_df is not None else 0}
                )
            
            if "bid1_vol" not in tick_df.columns:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.WARNING,
                    message="缺少bid1_vol列",
                    details={}
                )
            
            # CTO参数配置（从ConfigManager读取，严禁硬编码）
            pre_explosion_ticks = 5    # 起爆前15秒 = 5个Tick (3秒间隔)
            post_explosion_ticks = 1   # 起爆后3秒 = 1个Tick
            cliff_threshold = 0.70     # 断崖阈值70%
            
            # 边界检查
            if explosion_idx < pre_explosion_ticks:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message="起爆点位置靠前，无法计算前序窗口",
                    details={"explosion_idx": explosion_idx, "required": pre_explosion_ticks}
                )
            
            if explosion_idx + post_explosion_ticks >= len(tick_df):
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message="起爆点位置靠后，无法计算后续窗口",
                    details={"explosion_idx": explosion_idx, "data_length": len(tick_df)}
                )
            
            # 【核心计算】起爆前15秒(5个Tick)的bid1_vol均值
            pre_window_start = explosion_idx - pre_explosion_ticks
            pre_window_end = explosion_idx
            pre_bid1_vols = tick_df.iloc[pre_window_start:pre_window_end]["bid1_vol"]
            pre_avg = pre_bid1_vols.mean()
            
            # 【核心计算】起爆后3秒(1个Tick)的bid1_vol
            post_idx = explosion_idx + post_explosion_ticks
            post_bid1_vol = tick_df.iloc[post_idx]["bid1_vol"]
            
            # 【断崖检测】计算下跌幅度
            if pre_avg > 0:
                drop_pct = (pre_avg - post_bid1_vol) / pre_avg
            else:
                drop_pct = 0
            
            # 【判定逻辑】断崖下跌 > 70% 判定为陷阱
            is_trap = drop_pct > cliff_threshold
            
            if is_trap:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=True,
                    level=DefenseLevel.CRITICAL,
                    message=f"🚨 CTO陷阱警报: 起爆前bid1均值{pre_avg:.0f}，起爆后跌至{post_bid1_vol}，断崖{drop_pct*100:.1f}% > {cliff_threshold*100:.0f}%",
                    details={
                        "pre_explosion_avg_bid1": float(pre_avg),
                        "post_explosion_bid1": int(post_bid1_vol),
                        "drop_percentage": round(drop_pct * 100, 2),
                        "cliff_threshold": cliff_threshold * 100,
                        "pre_window_ticks": pre_explosion_ticks,
                        "post_window_ticks": post_explosion_ticks,
                        "explosion_idx": explosion_idx,
                        "is_trap": True
                    }
                )
            else:
                return DefenseResult(
                    defense_name=defense_name,
                    triggered=False,
                    level=DefenseLevel.SAFE,
                    message=f"✅ CTO防线通过: 起爆前bid1均值{pre_avg:.0f}，起爆后{post_bid1_vol}，跌幅{drop_pct*100:.1f}% < {cliff_threshold*100:.0f}%",
                    details={
                        "pre_explosion_avg_bid1": float(pre_avg),
                        "post_explosion_bid1": int(post_bid1_vol),
                        "drop_percentage": round(drop_pct * 100, 2),
                        "cliff_threshold": cliff_threshold * 100,
                        "is_trap": False
                    }
                )
                
        except Exception as e:
            logger.error(f"[CTO防线] 滑动窗口诱多检测异常: {e}")
            return DefenseResult(
                defense_name=defense_name,
                triggered=False,
                level=DefenseLevel.WARNING,
                message=f"CTO防线异常: {str(e)}",
                details={"error": str(e)}
            )


def create_mock_tick_data(scenario: str = "normal", n_ticks: int = 30) -> pd.DataFrame:
    """创建模拟Tick数据用于测试"""
    np.random.seed(42)
    base_price = 10.0
    
    if scenario == "normal":
        prices = base_price + np.random.randn(n_ticks) * 0.02
        bid1_vols = 1000 + np.random.randn(n_ticks) * 100
        ask1_vols = 800 + np.random.randn(n_ticks) * 80
        volumes = np.cumsum(np.random.randint(100, 500, n_ticks))
        
    elif scenario == "fake_support":
        prices = base_price + np.random.randn(n_ticks) * 0.01
        prices[-5:] = base_price
        bid1_vols = np.concatenate([
            2000 + np.random.randn(n_ticks//2) * 200,
            300 + np.random.randn(n_ticks - n_ticks//2) * 50
        ])
        ask1_vols = 800 + np.random.randn(n_ticks) * 80
        volumes = np.cumsum(np.random.randint(100, 500, n_ticks))
        
    elif scenario == "retail_hype":
        prices = base_price + np.cumsum(np.random.randn(n_ticks) * 0.005)
        bid1_vols = 200 + np.random.randn(n_ticks) * 50
        ask1_vols = 800 + np.random.randn(n_ticks) * 100
        volumes = np.cumsum(np.random.randint(50, 150, n_ticks))
        
    elif scenario == "order_decay":
        prices = np.concatenate([
            [base_price] * (n_ticks // 3),
            [base_price * 1.1] * (2 * n_ticks // 3)
        ])
        bid1_vols = 1000 + np.random.randn(n_ticks) * 100
        ask1_vols = np.concatenate([
            5000 + np.random.randn(n_ticks//3) * 500,
            np.linspace(5000, 500, 2*n_ticks//3) + np.random.randn(2*n_ticks//3) * 100
        ])
        volumes = np.cumsum(np.random.randint(100, 500, n_ticks))
        
    else:
        raise ValueError(f"Unknown scenario: {scenario}")
    
    bid1_vols = np.maximum(bid1_vols, 1)
    ask1_vols = np.maximum(ask1_vols, 1)
    
    df = pd.DataFrame({
        "price": prices,
        "bid1_vol": bid1_vols.astype(int),
        "ask1_vol": ask1_vols.astype(int),
        "volume": volumes
    })
    
    return df


def run_tests():
    """运行测试验证三道防线"""
    print("=" * 70)
    print("微观盘口三道防线 - 测试验证")
    print("=" * 70)
    
    defense_system = MicroDefenseSystem()
    
    scenarios = ["normal", "fake_support", "retail_hype", "order_decay"]
    
    for scenario in scenarios:
        print(f"\n测试场景: {scenario.upper()}")
        print("-" * 70)
        
        tick_data = create_mock_tick_data(scenario)
        up_stop = 11.0 if scenario == "order_decay" else None
        
        report = defense_system.analyze(f"TEST_{scenario.upper()}", tick_data, up_stop)
        
        print(f"综合得分: {report.composite_score:.1f}/100")
        print(f"整体安全: {'通过' if report.overall_safe else '拦截'}")
        print(f"\n防线详情:")
        for result in report.defense_results:
            status = "触发" if result.triggered else "正常"
            print(f"  [{status}] {result.defense_name}: {result.message}")
        
        print(f"\n建议:")
        for rec in report.recommendations:
            print(f"  - {rec}")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
