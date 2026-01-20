"""
半路战法模块 - V19 20cm加速战法

核心逻辑：
- 专攻创业板(300)和科创板(688)的20cm标的
- 捕捉分时均线支撑后的二次加速点
- 结合DDE资金流向确认

四大核心模式：
1. 平台突破战法（胜率最高）
2. 上影线反包战法
3. 阴线反包战法
4. 涨停加一阳战法（空中加油）

Author: iFlow CLI
Version: V19.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import talib
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.data_adapter_akshare import MoneyFlowAdapter

logger = get_logger(__name__)


@dataclass
class MidwaySignal:
    """半路战法信号"""
    stock_code: str
    stock_name: str
    signal_date: str
    signal_type: str  # 信号类型：平台突破、上影线反包、阴线反包、涨停加一阳
    entry_price: float
    stop_loss: float
    target_price: float
    signal_strength: float  # 信号强度 0-1
    risk_level: str  # 风险等级: '低', '中', '高'
    reasons: List[str]  # 信号理由
    confidence: float  # 置信度 0-1
    technical_indicators: Dict[str, float]  # 关键技术指标
    dde_net_inflow: float  # DDE净流入（元）


class MidwayStrategy:
    """
    半路战法 - 20cm加速战法
    
    专攻创业板/科创板的20cm标的，捕捉分时均线支撑后的二次加速点
    """

    def __init__(self, lookback_days: int = 30):
        """
        初始化半路战法分析器

        Args:
            lookback_days: 回看天数
        """
        self.lookback_days = lookback_days
        self.db = DataManager()
        self.money_flow = MoneyFlowAdapter()
        
        logger.info(f"🚀 [半路战法] 初始化完成，回看天数: {lookback_days}")

    def scan_market(self, min_change_pct: float = 3.0, max_change_pct: float = 12.0, 
                   min_score: float = 0.6, stock_limit: int = 50) -> List[Dict]:
        """
        扫描全市场20cm标的（300/688）
        
        Args:
            min_change_pct: 最小涨幅（默认3%）
            max_change_pct: 最大涨幅（默认12%，避免追高）
            min_score: 最低信号强度（默认0.6）
            stock_limit: 扫描股票数量限制（默认50只）
        
        Returns:
            List[Dict]: 符合条件的股票列表
        """
        logger.info(f"🚀 [半路战法] 开始扫描全市场20cm标的...")
        
        try:
            # 1. 获取全市场股票列表
            import akshare as ak
            stock_list_df = ak.stock_zh_a_spot_em()
            
            if stock_list_df.empty:
                logger.error("❌ [半路战法] 获取股票列表失败")
                return []
            
            # 2. 筛选20cm标的（300xxx和688xxx）
            stock_list_df = stock_list_df[
                stock_list_df['代码'].str.startswith(('300', '688'))
            ]
            
            # 3. 筛选涨幅在范围内的股票
            stock_list_df = stock_list_df[
                (stock_list_df['涨跌幅'] >= min_change_pct) & 
                (stock_list_df['涨跌幅'] <= max_change_pct)
            ]
            
            # 4. 按成交量排序，取最活跃的N只
            if '成交量' in stock_list_df.columns:
                stock_list_df = stock_list_df.sort_values('成交量', ascending=False)
            elif '成交额' in stock_list_df.columns:
                stock_list_df = stock_list_df.sort_values('成交额', ascending=False)
            
            stock_list_df = stock_list_df.head(stock_limit)
            
            logger.info(f"✅ [半路战法] 初筛完成，待分析股票: {len(stock_list_df)} 只")
            
            # 5. 获取实时数据
            stock_codes = stock_list_df['代码'].tolist()
            realtime_data = self.db.get_fast_price(stock_codes)
            
            if not realtime_data:
                logger.error("❌ [半路战法] 获取实时数据失败")
                return []
            
            # 🚀 V19.3 第三刀：优化扫描逻辑（只做减法）
            # Step 1: 获取全市场快照（已完成，stock_list_df 就是快照）
            # Step 2: 本地筛选 涨幅 > 2% 且 量比 > 1.5 的股票（剩下约 300 只）
            # Step 3: 只对这 300 只 调用 data_adapter 获取详细数据
            
            # 🚀 V19.3 新增：批量获取历史数据（用于计算量比）
            logger.info(f"🔄 [半路战法] 开始批量获取历史数据，计算量比...")
            history_data_cache = {}
            volume_ratio_cache = {}
            
            for code in stock_codes:
                try:
                    df = self.db.get_history_data(code)
                    if df is not None and len(df) >= 5:
                        history_data_cache[code] = df
                        
                        # 计算量比
                        # 检查是否有 turnover 列
                        if 'turnover' in df.columns:
                            avg_turnover = df['turnover'].tail(5).mean()  # 5日平均成交额
                            current_turnover = realtime_data.get(code, {}).get('turnover', 0)  # 当前成交额
                            if avg_turnover > 0:
                                volume_ratio = current_turnover / avg_turnover
                            else:
                                volume_ratio = 0
                        else:
                            # 如果没有 turnover 列，使用成交量计算
                            avg_volume = df['volume'].tail(5).mean() / 100  # 转换为手数
                            current_volume = realtime_data.get(code, {}).get('volume', 0) / 100  # 转换为手数
                            
                            # 如果平均成交量太小（<1000手），可能是停牌或数据异常，不计算量比
                            if avg_volume < 1000:
                                volume_ratio = 1  # 不计算，避免异常值
                            elif avg_volume > 0:
                                volume_ratio = current_volume / avg_volume
                            else:
                                volume_ratio = 0
                        
                        volume_ratio_cache[code] = volume_ratio
                except Exception as e:
                    logger.debug(f"[{code}] 获取历史数据失败: {e}")
                    continue
            
            logger.info(f"✅ [半路战法] 历史数据获取完成，成功获取 {len(history_data_cache)} 只股票")
            
            # 🚀 V19.3 新增：本地筛选（涨幅 > 2% 且 量比 > 1.5）
            filtered_stock_list_df = stock_list_df.copy()
            filtered_stock_list_df['量比'] = filtered_stock_list_df['代码'].map(volume_ratio_cache)
            
            # 筛选条件：涨幅 > 2% 且 量比 > 1.5
            filtered_stock_list_df = filtered_stock_list_df[
                (filtered_stock_list_df['涨跌幅'] > 2.0) & 
                (filtered_stock_list_df['量比'] > 1.5)
            ]
            
            logger.info(f"🎯 [半路战法] 本地筛选完成，从 {len(stock_list_df)} 只筛选到 {len(filtered_stock_list_df)} 只股票")
            
            # 如果筛选后没有股票，直接返回
            if filtered_stock_list_df.empty:
                logger.info("⚠️ [半路战法] 本地筛选后无符合条件的股票")
                return []
            
            # 更新股票代码列表
            filtered_stock_codes = filtered_stock_list_df['代码'].tolist()
            
            # 6. 批量获取DDE资金流向（只对筛选后的股票）
            dde_data = {}
            try:
                logger.info(f"🔄 [半路战法] 开始批量获取 DDE 数据，股票数量: {len(filtered_stock_codes)}")
                dde_data = self.money_flow.batch_get_dde(filtered_stock_codes)
                logger.info(f"✅ [半路战法] DDE 数据获取完成，成功获取 {len(dde_data)} 只股票")
            except Exception as e:
                logger.warning(f"⚠️ [半路战法] DDE数据获取失败: {e}")
            
            # 7. 逐个分析股票（只分析筛选后的股票）
            signals = []
            for idx, row in filtered_stock_list_df.iterrows():
                code = row['代码']
                name = row['名称']
                
                try:
                    # 🚀 V19.3 优化：从缓存中获取历史数据，避免重复查询
                    df = history_data_cache.get(code)
                    
                    if df is None or len(df) < 20:
                        logger.debug(f"[{code}] 数据不足，跳过")
                        continue
                    
                    # 分析半路战法信号
                    signal = self._analyze_midway_signal(df, code, name, realtime_data, dde_data)
                    
                    if signal and signal.signal_strength >= min_score:
                        signals.append(signal)
                        logger.info(f"✅ [半路战法] 发现信号: {name}({code}) - 强度: {signal.signal_strength:.2f}")
                
                except Exception as e:
                    logger.error(f"❌ [半路战法] 分析股票 {code} 失败: {e}")
                    continue
            
            # 8. 按信号强度排序
            signals.sort(key=lambda x: x.signal_strength, reverse=True)
            
            logger.info(f"🎯 [半路战法] 扫描完成，发现 {len(signals)} 个信号")
            
            # 9. 转换为字典格式
            result = []
            for s in signals:
                result.append({
                    'code': s.stock_code,
                    'name': s.stock_name,
                    'score': s.signal_strength,
                    'reason': '; '.join(s.reasons),
                    'current_price': s.entry_price,
                    'dde_net': s.dde_net_inflow,
                    'signal_type': s.signal_type,
                    'stop_loss': s.stop_loss,
                    'target_price': s.target_price,
                    'risk_level': s.risk_level,
                    'confidence': s.confidence
                })
            
            return result
        
        except Exception as e:
            logger.error(f"❌ [半路战法] 扫描失败: {e}")
            return []
    
    def _analyze_midway_signal(self, df: pd.DataFrame, code: str, name: str,
                               realtime_data: Dict, dde_data: Dict) -> Optional[MidwaySignal]:
        """
        分析半路战法信号
        
        Args:
            df: 历史K线数据
            code: 股票代码
            name: 股票名称
            realtime_data: 实时数据
            dde_data: DDE数据
        
        Returns:
            MidwaySignal: 信号对象，如果没有信号则返回None
        """
        # 计算技术指标
        df = self._calculate_indicators(df)
        
        # 获取DDE净流入
        dde_net = 0
        if code in dde_data:
            dde_net = dde_data[code].get('net_inflow', 0)
        elif code in realtime_data:
            dde_net = realtime_data[code].get('dde_net', 0)
        
        # 🚀 V19.4 盲扫模式：检查 DDE 数据状态
        dde_status = "资金共振"
        if dde_net == 0:
            dde_status = "⚠️ DDE缺失(纯形态)"
            logger.debug(f"[{code}] DDE 数据缺失，降级为【纯价格形态】模式")
        
        # 检查四大核心模式
        signals = []
        
        # 1. 平台突破战法
        platform_signal = self._check_platform_breakout(df, code, name, dde_net)
        if platform_signal:
            signals.append(platform_signal)
        
        # 2. 上影线反包战法
        shadow_signal = self._check_shadow_reversal(df, code, name, dde_net)
        if shadow_signal:
            signals.append(shadow_signal)
        
        # 3. 阴线反包战法
        bearish_signal = self._check_bearish_reversal(df, code, name, dde_net)
        if bearish_signal:
            signals.append(bearish_signal)

        # 4. 涨停加一阳战法
        limit_up_signal = self._check_limit_up_one_yang(df, code, name, dde_net)
        if limit_up_signal:
            signals.append(limit_up_signal)

        # 🆕 V19 新增：5. 分时形态识别（阶梯式上涨）
        stair_signal = self._check_stair_climbing_pattern(df, code, name, dde_net)
        if stair_signal:
            signals.append(stair_signal)

        # 选择评分最高的信号
        if signals:
            best_signal = max(signals, key=lambda x: x.signal_strength)
            return best_signal

        return None
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = df.copy()
        
        # 确保数据类型为float64
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].astype(float)
        
        # 移动平均线
        df['ma5'] = talib.SMA(df['close'].values, timeperiod=5)
        df['ma10'] = talib.SMA(df['close'].values, timeperiod=10)
        df['ma20'] = talib.SMA(df['close'].values, timeperiod=20)
        
        # 布林带
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(
            df['close'].values, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )
        
        # RSI
        df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)
        
        # MACD
        df['macd'], df['macdsignal'], df['macdhist'] = talib.MACD(
            df['close'].values, fastperiod=12, slowperiod=26, signalperiod=9
        )
        
        # 成交量指标
        df['volume_ma5'] = talib.SMA(df['volume'].values, timeperiod=5)
        df['volume_ratio'] = df['volume'] / df['volume_ma5']
        
        return df
    
    def _check_platform_breakout(self, df: pd.DataFrame, code: str, name: str, 
                                 dde_net: float) -> Optional[MidwaySignal]:
        """检查平台突破战法"""
        if len(df) < 20:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 检查是否突破平台
        recent_prices = df['close'].tail(10).values
        price_range = (recent_prices.max() - recent_prices.min()) / recent_prices.mean()
        
        if price_range > 0.03:
            return None
        
        if latest['close'] <= recent_prices.max():
            return None
        
        # 检查成交量
        if latest['volume'] < df['volume_ma5'].iloc[-1] * 1.2:
            return None
        
        # 检查RSI
        if latest['rsi'] > 80:
            return None
        
        # 计算信号强度
        signal_strength = 0.6
        
        if latest['volume'] > df['volume_ma5'].iloc[-1] * 2:
            signal_strength += 0.2
        elif latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
            signal_strength += 0.1
        
        if 40 < latest['rsi'] < 70:
            signal_strength += 0.1
        
        if latest['macdhist'] > 0:
            signal_strength += 0.1
        
        # DDE加分
        if dde_net > 0:
            signal_strength += 0.1
        
        signal_strength = min(signal_strength, 1.0)
        
        entry_price = latest['close']
        stop_loss = recent_prices.min()
        target_price = entry_price * 1.10
        
        risk_level = self._determine_risk_level(signal_strength, stop_loss, entry_price)
        
        reasons = [
            f"突破10天平台，震荡幅度{price_range*100:.1f}%",
            f"成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍",
            f"RSI={latest['rsi']:.1f}"
        ]
        
        # 🚀 V19.4 盲扫模式：DDE 加分逻辑
        if dde_net > 0:
            reasons.append(f"DDE净流入{dde_net/10000:.1f}万")
        elif dde_net == 0:
            reasons.append("⚠️ DDE缺失(纯形态)")
        
        return MidwaySignal(
            stock_code=code,
            stock_name=name,
            signal_date=str(latest.name),
            signal_type='平台突破',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_strength=signal_strength,
            risk_level=risk_level,
            reasons=reasons,
            confidence=signal_strength,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                'macd_hist': latest['macdhist']
            },
            dde_net_inflow=dde_net
        )
    
    def _check_shadow_reversal(self, df: pd.DataFrame, code: str, name: str,
                                dde_net: float) -> Optional[MidwaySignal]:
        """检查上影线反包战法"""
        if len(df) < 5:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        prev_upper_shadow = prev['high'] - max(prev['open'], prev['close'])
        prev_body = abs(prev['close'] - prev['open'])
        
        if prev_upper_shadow < prev_body * 2:
            return None
        
        if latest['close'] <= prev['high']:
            return None
        
        if latest['volume'] < df['volume_ma5'].iloc[-1]:
            return None
        
        if latest['rsi'] > 75:
            return None
        
        signal_strength = 0.5
        
        if prev_upper_shadow > prev_body * 3:
            signal_strength += 0.15
        elif prev_upper_shadow > prev_body * 2:
            signal_strength += 0.1
        
        if latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
            signal_strength += 0.15
        elif latest['volume'] > df['volume_ma5'].iloc[-1] * 1.2:
            signal_strength += 0.1
        
        if 40 < latest['rsi'] < 70:
            signal_strength += 0.1
        
        if latest['macdhist'] > 0:
            signal_strength += 0.1
        
        # 🚀 V19.4 盲扫模式：DDE 加分逻辑
        if dde_net > 0:
            signal_strength += 0.1
        
        signal_strength = min(signal_strength, 1.0)
        
        entry_price = latest['close']
        stop_loss = prev['low']
        target_price = entry_price * 1.10
        
        risk_level = self._determine_risk_level(signal_strength, stop_loss, entry_price)
        
        reasons = [
            f"上影线反包，上影线{prev_upper_shadow:.2f}，实体{prev_body:.2f}",
            f"突破前高{prev['high']:.2f}",
            f"成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍"
        ]
        
        # 🚀 V19.4 盲扫模式：DDE 加分逻辑
        if dde_net > 0:
            reasons.append(f"DDE净流入{dde_net/10000:.1f}万")
        elif dde_net == 0:
            reasons.append("⚠️ DDE缺失(纯形态)")
        
        return MidwaySignal(
            stock_code=code,
            stock_name=name,
            signal_date=str(latest.name),
            signal_type='上影线反包',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_strength=signal_strength,
            risk_level=risk_level,
            reasons=reasons,
            confidence=signal_strength,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                'macd_hist': latest['macdhist']
            },
            dde_net_inflow=dde_net
        )
    
    def _check_bearish_reversal(self, df: pd.DataFrame, code: str, name: str,
                                 dde_net: float) -> Optional[MidwaySignal]:
        """检查阴线反包战法"""
        if len(df) < 5:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        if prev['close'] >= prev['open']:
            return None
        
        if prev['volume'] > df['volume_ma5'].iloc[-2] * 1.2:
            return None
        
        if latest['close'] <= prev['open']:
            return None
        
        if latest['volume'] < df['volume_ma5'].iloc[-1] * 1.2:
            return None
        
        if latest['rsi'] > 75:
            return None
        
        signal_strength = 0.5
        
        if prev['volume'] < df['volume_ma5'].iloc[-2] * 0.7:
            signal_strength += 0.15
        elif prev['volume'] < df['volume_ma5'].iloc[-2] * 0.9:
            signal_strength += 0.1
        
        if latest['volume'] > df['volume_ma5'].iloc[-1] * 2:
            signal_strength += 0.15
        elif latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
            signal_strength += 0.1
        
        if 35 < latest['rsi'] < 65:
            signal_strength += 0.1
        
        if latest['macdhist'] > 0:
            signal_strength += 0.1
        
        # DDE加分
        if dde_net > 0:
            signal_strength += 0.1
        
        signal_strength = min(signal_strength, 1.0)
        
        entry_price = latest['close']
        stop_loss = prev['low']
        target_price = entry_price * 1.10
        
        risk_level = self._determine_risk_level(signal_strength, stop_loss, entry_price)
        
        reasons = [
            f"阴线反包，前日缩量下跌{abs(prev['close']-prev['open'])/prev['open']*100:.1f}%",
            f"今日放量反包，成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍",
            f"RSI={latest['rsi']:.1f}"
        ]
        
        # 🚀 V19.4 盲扫模式：DDE 加分逻辑
        if dde_net > 0:
            reasons.append(f"DDE净流入{dde_net/10000:.1f}万")
        elif dde_net == 0:
            reasons.append("⚠️ DDE缺失(纯形态)")
        
        return MidwaySignal(
            stock_code=code,
            stock_name=name,
            signal_date=str(latest.name),
            signal_type='阴线反包',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_strength=signal_strength,
            risk_level=risk_level,
            reasons=reasons,
            confidence=signal_strength,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                'macd_hist': latest['macdhist']
            },
            dde_net_inflow=dde_net
        )
    
    def _check_limit_up_one_yang(self, df: pd.DataFrame, code: str, name: str,
                                  dde_net: float) -> Optional[MidwaySignal]:
        """检查涨停加一阳战法"""
        if len(df) < 5:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) >= 3 else None
        
        if prev2 is None:
            return None
        
        prev2_change = (prev2['close'] - prev2['open']) / prev2['open']
        if prev2_change < 0.09:
            return None
        
        prev_upper_shadow = prev['high'] - max(prev['open'], prev['close'])
        prev_body = abs(prev['close'] - prev['open'])
        
        if prev['close'] < prev['open']:
            return None
        
        if latest['close'] <= prev['close']:
            return None
        
        if latest['volume'] < df['volume_ma5'].iloc[-1]:
            return None
        
        if latest['rsi'] > 80:
            return None
        
        signal_strength = 0.5
        
        if prev_upper_shadow > prev_body:
            signal_strength += 0.1
        
        if latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
            signal_strength += 0.15
        elif latest['volume'] > df['volume_ma5'].iloc[-1] * 1.2:
            signal_strength += 0.1
        
        if 40 < latest['rsi'] < 70:
            signal_strength += 0.15
        elif 30 < latest['rsi'] <= 40:
            signal_strength += 0.1
        
        if latest['macdhist'] > 0:
            signal_strength += 0.1
        
        # DDE加分
        if dde_net > 0:
            signal_strength += 0.1
        
        signal_strength = min(signal_strength, 1.0)
        
        entry_price = latest['close']
        stop_loss = prev2['low']
        target_price = entry_price * 1.12
        
        risk_level = self._determine_risk_level(signal_strength, stop_loss, entry_price)
        
        reasons = [
            f"涨停加一阳，前日涨停{prev2_change*100:.1f}%",
            f"昨日调整后今日上涨{abs(latest['close']-prev['close'])/prev['close']*100:.1f}%",
            f"成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍"
        ]
        
        # 🚀 V19.4 盲扫模式：DDE 加分逻辑
        if dde_net > 0:
            reasons.append(f"DDE净流入{dde_net/10000:.1f}万")
        elif dde_net == 0:
            reasons.append("⚠️ DDE缺失(纯形态)")

        return MidwaySignal(
            stock_code=code,
            stock_name=name,
            signal_date=str(latest.name),
            signal_type='涨停加一阳',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_strength=signal_strength,
            risk_level=risk_level,
            reasons=reasons,
            confidence=signal_strength,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                'macd_hist': latest['macdhist']
            },
            dde_net_inflow=dde_net
        )

    def _check_stair_climbing_pattern(self, df: pd.DataFrame, code: str, name: str,
                                     dde_net: float) -> Optional[MidwaySignal]:
        """
        🆕 V19 新增：检查阶梯式上涨模式（分时形态识别）

        阶梯式上涨特征：
        1. 价格呈现台阶式上涨，每个台阶有明显的横盘整理
        2. 每个台阶的上涨幅度在3%-8%之间
        3. 每个台阶的整理时间在2-5根K线之间
        4. 成交量在上涨时放大，整理时缩量
        5. 当前处于新的台阶突破点

        Args:
            df: 历史K线数据
            code: 股票代码
            name: 股票名称
            dde_net: DDE净流入

        Returns:
            MidwaySignal: 信号对象，如果没有信号则返回None
        """
        if len(df) < 15:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 1. 检测阶梯式上涨模式
        # 使用最近15根K线来检测阶梯模式
        recent_df = df.tail(15).copy()

        # 计算价格变化
        recent_df['price_change'] = recent_df['close'].pct_change()

        # 检测台阶：价格连续上涨后横盘整理
        steps = []
        current_step_start = 0
        current_step_high = recent_df.iloc[0]['high']
        current_step_low = recent_df.iloc[0]['low']

        for i in range(1, len(recent_df)):
            row = recent_df.iloc[i]

            # 检测是否开始新的台阶（价格突破前一个台阶的高点）
            if row['close'] > current_step_high * 1.03:  # 上涨超过3%
                # 保存上一个台阶
                if i - current_step_start >= 2:  # 台阶至少持续2根K线
                    steps.append({
                        'start': current_step_start,
                        'end': i - 1,
                        'high': current_step_high,
                        'low': current_step_low,
                        'rise_pct': (current_step_high - current_step_low) / current_step_low
                    })

                # 开始新的台阶
                current_step_start = i
                current_step_high = row['high']
                current_step_low = row['low']

            # 更新当前台阶的高低点
            current_step_high = max(current_step_high, row['high'])
            current_step_low = min(current_step_low, row['low'])

        # 检查是否有至少2个台阶
        if len(steps) < 2:
            return None

        # 2. 检查当前是否处于新的台阶突破点
        last_step = steps[-1]
        latest_step_start = last_step['end'] + 1

        # 检查最近2根K线是否突破了最后一个台阶的高点
        if latest['close'] <= last_step['high'] * 1.02:
            return None

        # 3. 检查成交量
        # 突破时成交量应该放大
        if latest['volume'] < df['volume_ma5'].iloc[-1] * 1.3:
            return None

        # 4. 检查RSI
        if latest['rsi'] > 80:
            return None

        # 🚀 V19.4 盲扫模式：解除资金流否决权
        # 如果 DDE 为 0 (说明接口挂了)，暂时放行，标记为 [无资金数据]
        if dde_net < 0:
            return None  # DDE流出才拒绝
        elif dde_net == 0:
            # DDE 为 0，降级为纯价格形态模式
            pass  # 不做任何操作，继续执行

        # 6. 计算信号强度
        signal_strength = 0.6

        # 台阶数量加分（台阶越多，信号越强）
        signal_strength += min(len(steps) * 0.05, 0.15)

        # 每个台阶的上涨幅度加分
        avg_rise_pct = sum(s['rise_pct'] for s in steps) / len(steps)
        if 0.03 <= avg_rise_pct <= 0.08:
            signal_strength += 0.1

        # 成交量放大加分
        volume_ratio = latest['volume'] / df['volume_ma5'].iloc[-1]
        if volume_ratio >= 2.0:
            signal_strength += 0.1
        elif volume_ratio >= 1.5:
            signal_strength += 0.05

        # MACD加分
        if latest['macdhist'] > 0:
            signal_strength += 0.05

        # DDE加分
        if dde_net > 1000000:  # DDE净流入超过100万
            signal_strength += 0.1
        elif dde_net > 0:
            signal_strength += 0.05

        signal_strength = min(signal_strength, 1.0)

        # 计算止损和目标价
        entry_price = latest['close']
        stop_loss = last_step['low']  # 止损设在上一个台阶的低点
        target_price = entry_price * 1.10  # 目标价设为10%涨幅

        risk_level = self._determine_risk_level(signal_strength, stop_loss, entry_price)

        # 生成原因描述
        reasons = [
            f"阶梯式上涨模式，检测到{len(steps)}个台阶",
            f"平均每个台阶上涨{avg_rise_pct*100:.1f}%",
            f"当前突破最后一个台阶高点{last_step['high']:.2f}",
            f"成交量放大{volume_ratio:.2f}倍"
        ]

        # 🚀 V19.4 盲扫模式：DDE 加分逻辑
        if dde_net > 0:
            reasons.append(f"DDE净流入{dde_net/10000:.1f}万")
        elif dde_net == 0:
            reasons.append("⚠️ DDE缺失(纯形态)")

        return MidwaySignal(
            stock_code=code,
            stock_name=name,
            signal_date=str(latest.name),
            signal_type='阶梯式上涨',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_strength=signal_strength,
            risk_level=risk_level,
            reasons=reasons,
            confidence=signal_strength,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': volume_ratio,
                'macd_hist': latest['macdhist'],
                'steps_count': len(steps),
                'avg_rise_pct': avg_rise_pct
            },
            dde_net_inflow=dde_net
        )

    def _determine_risk_level(self, signal_strength: float, stop_loss: float,
                              entry_price: float) -> str:
        """确定风险等级"""
        risk_ratio = abs(entry_price - stop_loss) / entry_price
        
        if signal_strength >= 0.8 and risk_ratio <= 0.05:
            return '低'
        elif signal_strength >= 0.6 and risk_ratio <= 0.08:
            return '中'
        else:
            return '高'