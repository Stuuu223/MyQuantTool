"""
买点扫描器：实时扫描符合买点条件的股票

参考文献：
- https://caifuhao.eastmoney.com/news/20190816224355084524130
- https://xueqiu.com/2307830329/356110729
- http://www.10huang.cn/buy/54536.html
- http://www.10huang.cn/buy/55110.html (对称三角形突破)
- http://www.10huang.cn/zhangting/54559.html (预期差买点)
- http://www.10huang.cn/zhangting/54332.html (冰点买点)

核心逻辑：
- 逻辑面 > 情绪面 > 资金面 > 技术面
- 大盘 > 板块 > 个股
- 技术面突破
- 资金流入
- 情绪指标配合
- 风险控制阈值

核心买点模式：
1. 对称三角形突破买点
2. 预期差买点（龙头核心模式）
3. 冰点买点（衰竭性冰点）
4. 突破买点
5. 回调买点
6. 金叉买点
7. 背离买点
8. 弱信号（潜在机会）
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import talib
from .data_source_manager import DataSourceManager


@dataclass
class BuySignal:
    """买点信号"""
    stock_code: str
    stock_name: str
    scan_date: str
    signal_type: str  # 信号类型
    entry_price: float  # 入场价
    stop_loss: float  # 止损价
    target_price: float  # 目标价
    signal_score: float  # 信号评分 0-100
    risk_level: str  # 风险等级: '低', '中', '高'
    reasons: List[str]  # 信号理由
    technical_indicators: Dict[str, float]  # 关键技术指标值


class BuyPointScanner:
    """买点扫描器"""

    def __init__(self, db=None):
        """
        初始化买点扫描器

        Args:
            db: 数据库连接
        """
        self.data_manager = DataSourceManager(db) if db else None

    def scan_buy_signals(self, stock_list: List[str] = None, stock_info: Dict[str, str] = None, market: str = 'A') -> List[BuySignal]:
        """
        扫描买点信号

        Args:
            stock_list: 股票代码列表，如果为None则扫描全市场
            stock_info: 股票信息字典 {股票代码: 股票名称}
            market: 市场类型，'A'表示A股

        Returns:
            List[BuySignal]: 买点信号列表
        """
        if stock_list is None:
            # 如果没有提供股票列表，可以获取全市场股票代码
            # 这里简化处理，实际应用中需要从数据库或API获取
            stock_list = self._get_stock_list(market)

        if stock_info is None:
            stock_info = {}

        signals = []
        for stock_code in stock_list:
            try:
                # 获取股票数据
                df = self._get_stock_data(stock_code)
                if df is not None and len(df) >= 30:  # 确保有足够的数据
                    stock_name = stock_info.get(stock_code, None)
                    signal = self._analyze_single_stock(df, stock_code, stock_name)
                    if signal:
                        signals.append(signal)
            except Exception as e:
                # 记录错误但继续处理其他股票
                print(f"处理股票 {stock_code} 时出错: {e}")
                continue

        # 按信号评分排序
        signals.sort(key=lambda x: x.signal_score, reverse=True)

        # 降低门槛，返回评分≥40的信号（原为60）
        filtered_signals = [s for s in signals if s.signal_score >= 40]

        # 添加调试信息
        print(f"[扫描统计] 共扫描 {len(stock_list) if stock_list else 0} 只股票")
        print(f"[扫描统计] 发现 {len(signals)} 个信号（评分≥0）")
        print(f"[扫描统计] 过滤后 {len(filtered_signals)} 个信号（评分≥40）")

        return filtered_signals

    def _get_stock_list(self, market: str) -> List[str]:
        """
        获取股票列表（简化实现，实际应用中应从数据库或API获取）
        """
        # 这里仅作示例返回几个股票代码
        # 实际应用中应连接数据库或API获取全市场股票代码
        return ['000001', '000002', '600000', '600036']  # 示例股票

    def _get_stock_data(self, stock_code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """
        获取股票数据

        Args:
            stock_code: 股票代码
            days: 获取天数

        Returns:
            pd.DataFrame: 股票数据
        """
        # 使用数据源管理器获取数据
        if self.data_manager:
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            return self.data_manager.get_stock_data(stock_code, start_date, end_date)
        else:
            # 如果没有数据管理器，返回None（实际应用中应该有其他方式获取数据）
            return None

    def _analyze_single_stock(self, df: pd.DataFrame, stock_code: str, stock_name: str = None) -> Optional[BuySignal]:
        """分析单个股票的买点信号
        
        Args:
            df: 股票数据
            stock_code: 股票代码
            stock_name: 股票名称（可选）
        """
        try:
            # 计算技术指标
            df = self._calculate_technical_indicators(df)
            latest = df.iloc[-1]

            # 获取股票名称
            if stock_name is None:
                stock_name = f"股票_{stock_code}"

            # 检查各种买点模式
            signals = []

            # 1. 对称三角形突破买点（新增）
            triangle_signal = self._check_triangle_breakout(df, stock_code, stock_name)
            if triangle_signal:
                signals.append(triangle_signal)

            # 2. 预期差买点（新增）
            expectation_signal = self._check_expectation_gap(df, stock_code, stock_name)
            if expectation_signal:
                signals.append(expectation_signal)

            # 3. 冰点买点（新增）
            ice_point_signal = self._check_ice_point(df, stock_code, stock_name)
            if ice_point_signal:
                signals.append(ice_point_signal)

            # 4. 突破买点
            breakout_signal = self._check_breakout_signal(df, stock_code, stock_name)
            if breakout_signal:
                signals.append(breakout_signal)

            # 5. 回调买点
            pullback_signal = self._check_pullback_signal(df, stock_code, stock_name)
            if pullback_signal:
                signals.append(pullback_signal)

            # 6. 金叉买点
            golden_cross_signal = self._check_golden_cross_signal(df, stock_code, stock_name)
            if golden_cross_signal:
                signals.append(golden_cross_signal)

            # 7. 背离买点
            divergence_signal = self._check_divergence_signal(df, stock_code, stock_name)
            if divergence_signal:
                signals.append(divergence_signal)

            # 🆕 V19.6 新增：8. 量价齐升买点
            volume_price_signal = self._check_volume_price_rise(df, stock_code, stock_name)
            if volume_price_signal:
                signals.append(volume_price_signal)

            # 🆕 V19.6 新增：9. 缩量回调买点
            shrinkage_signal = self._check_shrinkage_pullback(df, stock_code, stock_name)
            if shrinkage_signal:
                signals.append(shrinkage_signal)

            # 🆕 V19.6 新增：10. 突破前高买点
            breakout_high_signal = self._check_breakout_high(df, stock_code, stock_name)
            if breakout_high_signal:
                signals.append(breakout_high_signal)

            # 11. 弱信号检测（如果没找到强信号，检查弱信号）
            if not signals:
                weak_signal = self._check_weak_signal(df, stock_code, stock_name)
                if weak_signal:
                    signals.append(weak_signal)

            # 选择评分最高的信号
            if signals:
                best_signal = max(signals, key=lambda x: x.signal_score)
                return best_signal

            return None
        except Exception as e:
            import traceback
            print(f"分析股票 {stock_code} 时出错: {type(e).__name__}: {e}")
            print(f"堆栈: {traceback.format_exc()}")
            return None

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        # 确保数据类型为float64（talib要求）
        df = df.copy()
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].astype(float)

        # 移动平均线
        df['ma5'] = talib.SMA(df['close'].values, timeperiod=5)
        df['ma10'] = talib.SMA(df['close'].values, timeperiod=10)
        df['ma20'] = talib.SMA(df['close'].values, timeperiod=20)
        df['ma60'] = talib.SMA(df['close'].values, timeperiod=60)

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

        # KDJ (使用STOCH计算，然后计算J值)
        slowk, slowd = talib.STOCH(
            df['high'].values, df['low'].values, df['close'].values,
            fastk_period=9, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0
        )
        df['k'] = slowk
        df['d'] = slowd
        df['j'] = 3 * df['k'] - 2 * df['d']  # J = 3K - 2D

        # 成交量指标
        df['volume_ma5'] = talib.SMA(df['volume'].values, timeperiod=5)
        df['volume_ratio'] = df['volume'] / df['volume_ma5']

        # CCI
        df['cci'] = talib.CCI(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)

        # 动量指标
        df['mom'] = talib.MOM(df['close'].values, timeperiod=10)

        # 波动率
        df['volatility'] = df['close'].rolling(window=10).std()

        return df

    def _check_breakout_signal(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[BuySignal]:
        """检查突破买点信号"""
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else latest

        # 检查向上突破
        price_breakout = latest['close'] > latest['ma10'] and latest['close'] > latest['ma20']
        volume_confirmation = latest['volume'] > latest['volume_ma5'] * 1.2  # 成交量确认
        momentum_positive = latest['mom'] > 0  # 动量向上

        if price_breakout and volume_confirmation and momentum_positive:
            # 基础分50分（满足突破条件）
            score = 50

            # RSI加分（避免超买）
            if latest['rsi'] < 50:  # RSI较低，空间大
                score += 20
            elif latest['rsi'] < 70:
                score += 10

            # 成交量加分
            if latest['volume_ratio'] > 2.0:
                score += 15
            elif latest['volume_ratio'] > 1.5:
                score += 10

            # 动量加分
            if latest['mom'] > np.mean(df['mom'].tail(5)) * 1.2:
                score += 15
            elif latest['mom'] > np.mean(df['mom'].tail(5)):
                score += 5

            # 设置入场价、止损价、目标价
            entry_price = latest['close']
            stop_loss = latest['ma10'] * 0.97  # MA10下方3%作为止损
            target_price = entry_price * 1.10  # 10%目标

            # 计算风险等级
            risk_level = self._determine_risk_level(abs(entry_price - stop_loss) / entry_price)

            return BuySignal(
                stock_code=stock_code,
                stock_name=stock_name,
                scan_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
                signal_type='突破买点',
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                signal_score=min(score, 100),
                risk_level=risk_level,
                reasons=[
                    f"向上突破MA10和MA20，确认突破有效",
                    f"成交量放大{latest['volume_ratio']:.2f}倍",
                    f"MOM动量指标向上确认趋势强度"
                ],
                technical_indicators={
                    'rsi': latest['rsi'],
                    'macd': latest['macd'],
                    'volume_ratio': latest['volume_ratio']
                }
            )

        return None

    def _check_pullback_signal(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[BuySignal]:
        """检查回调买点信号"""
        latest = df.iloc[-1]

        # 检查是否在重要均线附近企稳
        ma_support = (abs(latest['close'] - latest['ma5']) / latest['ma5'] < 0.02 or
                      abs(latest['close'] - latest['ma10']) / latest['ma10'] < 0.02)

        # RSI从超卖区域回升
        rsi_improvement = (latest['rsi'] > 30 and latest['rsi'] > df['rsi'].iloc[-2] if len(df) >= 2 else False)

        # 成交量萎缩后放大
        volume_pattern = self._check_volume_pullback_pattern(df)

        if ma_support and rsi_improvement and volume_pattern:
            # 基础分50分（满足回调条件）
            score = 50

            # 均线支撑加分
            if ma_support:
                score += 15

            # RSI加分
            if 30 < latest['rsi'] < 40:  # RSI在理想区间
                score += 20
            elif 40 <= latest['rsi'] < 50:
                score += 10

            # 成交量加分
            if volume_pattern:
                score += 15

            # 设置入场价、止损价、目标价
            entry_price = latest['close']
            stop_loss = min(latest['low'], latest['ma10'] * 0.97)  # 较低的止损
            target_price = entry_price * 1.08  # 8%目标

            risk_level = self._determine_risk_level(abs(entry_price - stop_loss) / entry_price)

            return BuySignal(
                stock_code=stock_code,
                stock_name=stock_name,
                scan_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
                signal_type='回调买点',
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                signal_score=min(score, 100),
                risk_level=risk_level,
                reasons=[
                    f"价格在MA5/MA10附近企稳，获得均线支撑",
                    f"RSI从超卖区回升至{latest['rsi']:.1f}，下跌动能减弱",
                    f"成交量萎缩后放大，显示资金重新关注"
                ],
                technical_indicators={
                    'rsi': latest['rsi'],
                    'ma_support': 'MA5/MA10附近',
                    'volume_ratio': latest['volume_ratio']
                }
            )

        return None

    def _check_volume_pullback_pattern(self, df: pd.DataFrame) -> bool:
        """检查成交量回调模式（萎缩后放大）"""
        if len(df) < 5:
            return False

        recent_volumes = df['volume'].tail(5).values

        # 检查是否先萎缩后放大
        volume_shrink = recent_volumes[-2] < recent_volumes[-3] and recent_volumes[-2] < recent_volumes[-4]
        volume_expand = recent_volumes[-1] > recent_volumes[-2] * 1.3

        return volume_shrink and volume_expand

    def _check_golden_cross_signal(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[BuySignal]:
        """检查金叉买点信号（MACD或KDJ金叉）"""
        if len(df) < 3:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # MACD金叉
        macd_golden = (latest['macdsignal'] > latest['macd']) and (prev['macdsignal'] <= prev['macd'])
        # KDJ金叉
        kdj_golden = (latest['k'] > latest['d']) and (prev['k'] <= prev['d']) and latest['k'] < 80

        if macd_golden or kdj_golden:
            # 基础分50分（满足金叉条件）
            score = 50

            # 金叉类型加分
            if macd_golden:
                score += 20
            if kdj_golden:
                score += 15

            # RSI加分
            if 40 < latest['rsi'] < 60:  # RSI在理想区间
                score += 15
            elif 30 < latest['rsi'] < 70:
                score += 10

            # 设置入场价、止损价、目标价
            entry_price = latest['close']
            stop_loss = latest['low'] * 0.96  # 最低价下方4%作为保守止损
            target_price = entry_price * 1.12  # 12%目标

            risk_level = self._determine_risk_level(abs(entry_price - stop_loss) / entry_price)

            signal_type = "MACD金叉" if macd_golden else "KDJ金叉"
            reasons = [
                f"{signal_type}形成，显示短期上涨动能",
                f"RSI处于{latest['rsi']:.1f}，技术指标健康",
                "成交量配合良好，确认信号有效性"
            ]

            return BuySignal(
                stock_code=stock_code,
                stock_name=stock_name,
                scan_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                signal_score=min(score, 100),
                risk_level=risk_level,
                reasons=reasons,
                technical_indicators={
                    'rsi': latest['rsi'],
                    'macd_hist': latest['macdhist'],
                    'kdj_j': latest['j']
                }
            )

        return None

    def _check_divergence_signal(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[BuySignal]:
        """检查背离买点信号"""
        if len(df) < 20:
            return None

        # 寻找价格新低但RSI不创新低的底背离
        price_lowest = df['low'].tail(10).idxmin() == df.index[-1]  # 最近创近期新低
        rsi_not_lowest = df['rsi'].tail(10).idxmin() != df.index[-1]  # 但RSI未创新低

        if price_lowest and rsi_not_lowest:
            # 基础分55分（底背离是较强的反转信号）
            score = 55

            # MACD柱状图向上加分
            if df['macdhist'].iloc[-1] > df['macdhist'].iloc[-2]:
                score += 20

            # 成交量配合加分
            if df['volume_ratio'].iloc[-1] > 1.2:
                score += 15
            elif df['volume_ratio'].iloc[-1] > 1.0:
                score += 10

            # 设置入场价、止损价、目标价
            entry_price = df['close'].iloc[-1]
            stop_loss = df['low'].iloc[-1] * 0.95  # 当日最低价下方5%作为止损
            target_price = entry_price * 1.15  # 15%目标（背离信号较强）

            risk_level = self._determine_risk_level(abs(entry_price - stop_loss) / entry_price)

            return BuySignal(
                stock_code=stock_code,
                stock_name=stock_name,
                scan_date=df.index[-1].strftime('%Y-%m-%d') if hasattr(df.index[-1], 'strftime') else str(df.index[-1]),
                signal_type='底背离买点',
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                signal_score=min(score, 100),
                risk_level=risk_level,
                reasons=[
                    f"价格创近期新低但RSI未创新低，形成底背离",
                    f"技术指标与价格走势背离，显示下跌动能衰竭",
                    f"MACD柱状图向上，显示上涨动能开始积聚"
                ],
                technical_indicators={
                    'rsi': df['rsi'].iloc[-1],
                    'price_lowest': True,
                    'rsi_not_lowest': True
                }
            )

        return None

    def _check_volume_price_rise(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[BuySignal]:
        """检查量价齐升买点"""
        if len(df) < 10:
            return None

        latest = df.iloc[-1]

        # 检查是否量价齐升
        # 价格上涨
        price_rise = latest['close'] > latest['open']
        # 成交量放大
        volume_rise = latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5
        # RSI健康
        rsi_healthy = 30 < latest['rsi'] < 70

        if price_rise and volume_rise and rsi_healthy:
            # 基础分50分
            score = 50

            # 成交量越大，加分
            if latest['volume'] > df['volume_ma5'].iloc[-1] * 2.5:
                score += 20
            elif latest['volume'] > df['volume_ma5'].iloc[-1] * 2.0:
                score += 15
            elif latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
                score += 10

            # RSI越健康，加分
            if 40 < latest['rsi'] < 60:
                score += 15
            elif 30 < latest['rsi'] < 70:
                score += 10

            # MACD加分
            if latest['macdhist'] > 0:
                score += 15

            score = min(score, 100)

            # 计算入场价、止损价、目标价
            entry_price = latest['close']
            stop_loss = latest['low'] * 0.97
            target_price = entry_price * 1.10

            risk_level = self._determine_risk_level(abs(entry_price - stop_loss) / entry_price)

            reasons = [
                f"量价齐升，成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍",
                f"RSI={latest['rsi']:.1f}，技术指标健康",
                f"MACD柱状图={latest['macdhist']:.4f}，上涨动能"
            ]

            print(f"[量价齐升买点] {stock_code} - 信号评分: {score}")

            return BuySignal(
                stock_code=stock_code,
                stock_name=stock_name,
                scan_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
                signal_type='量价齐升',
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                signal_score=score,
                risk_level=risk_level,
                reasons=reasons,
                technical_indicators={
                    'rsi': latest['rsi'],
                    'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                    'macd_hist': latest['macdhist']
                }
            )

        return None

    def _check_shrinkage_pullback(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[BuySignal]:
        """检查缩量回调买点"""
        if len(df) < 15:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 检查是否缩量回调
        # 价格小幅回调
        price_pullback = latest['close'] < prev['close'] and (prev['close'] - latest['close']) / prev['close'] < 0.03
        # 成交量萎缩
        volume_shrink = latest['volume'] < df['volume_ma5'].iloc[-1] * 0.8
        # 价格在均线附近
        ma_support = abs(latest['close'] - latest['ma10']) / latest['ma10'] < 0.02

        if price_pullback and volume_shrink and ma_support:
            # 基础分50分
            score = 50

            # 缩量越明显，加分
            if latest['volume'] < df['volume_ma5'].iloc[-1] * 0.6:
                score += 20
            elif latest['volume'] < df['volume_ma5'].iloc[-1] * 0.7:
                score += 15
            elif latest['volume'] < df['volume_ma5'].iloc[-1] * 0.8:
                score += 10

            # 回调幅度越小，加分
            pullback_pct = (prev['close'] - latest['close']) / prev['close']
            if pullback_pct < 0.01:
                score += 15
            elif pullback_pct < 0.02:
                score += 10
            elif pullback_pct < 0.03:
                score += 5

            # RSI加分
            if 35 < latest['rsi'] < 50:
                score += 15

            score = min(score, 100)

            # 计算入场价、止损价、目标价
            entry_price = latest['close']
            stop_loss = latest['low'] * 0.96
            target_price = entry_price * 1.08

            risk_level = self._determine_risk_level(abs(entry_price - stop_loss) / entry_price)

            reasons = [
                f"缩量回调，成交量萎缩{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍",
                f"价格在MA10附近企稳，回调幅度{pullback_pct*100:.2f}%",
                f"RSI={latest['rsi']:.1f}，处于合理区间"
            ]

            print(f"[缩量回调买点] {stock_code} - 信号评分: {score}")

            return BuySignal(
                stock_code=stock_code,
                stock_name=stock_name,
                scan_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
                signal_type='缩量回调',
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                signal_score=score,
                risk_level=risk_level,
                reasons=reasons,
                technical_indicators={
                    'rsi': latest['rsi'],
                    'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                    'ma_support': 'MA10附近'
                }
            )

        return None

    def _check_breakout_high(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[BuySignal]:
        """检查突破前高买点"""
        if len(df) < 20:
            return None

        latest = df.iloc[-1]

        # 检查是否突破前高
        # 找到最近20天的高点
        recent_high = df['high'].tail(20).max()
        # 今天突破前高
        breakout = latest['close'] > recent_high
        # 成交量确认
        volume_confirm = latest['volume'] > df['volume_ma5'].iloc[-1] * 1.3
        # RSI不超买
        rsi_ok = latest['rsi'] < 75

        if breakout and volume_confirm and rsi_ok:
            # 基础分60分（突破前高是较强信号）
            score = 60

            # 突破幅度越大，加分
            breakout_pct = (latest['close'] - recent_high) / recent_high
            if breakout_pct > 0.03:
                score += 15
            elif breakout_pct > 0.02:
                score += 10
            elif breakout_pct > 0.01:
                score += 5

            # 成交量越大，加分
            if latest['volume'] > df['volume_ma5'].iloc[-1] * 2.0:
                score += 15
            elif latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
                score += 10

            # RSI越健康，加分
            if 40 < latest['rsi'] < 60:
                score += 10
            elif 30 < latest['rsi'] < 70:
                score += 5

            score = min(score, 100)

            # 计算入场价、止损价、目标价
            entry_price = latest['close']
            stop_loss = recent_high * 0.97
            target_price = entry_price * 1.12

            risk_level = self._determine_risk_level(abs(entry_price - stop_loss) / entry_price)

            reasons = [
                f"突破前高{recent_high:.2f}，突破幅度{breakout_pct*100:.2f}%",
                f"成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍",
                f"RSI={latest['rsi']:.1f}，上涨动能充足"
            ]

            print(f"[突破前高买点] {stock_code} - 信号评分: {score}")

            return BuySignal(
                stock_code=stock_code,
                stock_name=stock_name,
                scan_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
                signal_type='突破前高',
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                signal_score=score,
                risk_level=risk_level,
                reasons=reasons,
                technical_indicators={
                    'rsi': latest['rsi'],
                    'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                    'breakout_high': recent_high
                }
            )

        return None

    def _check_weak_signal(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[BuySignal]:
        """检查弱信号（条件较宽松，评分较低）"""
        latest = df.iloc[-1]

        # 基础分35分
        score = 35

        # 检查是否有任何积极的信号
        reasons = []

        # 1. RSI超卖回升
        if latest['rsi'] < 40 and latest['rsi'] > df['rsi'].iloc[-2]:
            score += 10
            reasons.append(f"RSI从超卖区回升至{latest['rsi']:.1f}")

        # 2. MACD柱状图向上
        if df['macdhist'].iloc[-1] > df['macdhist'].iloc[-2]:
            score += 10
            reasons.append("MACD柱状图向上")

        # 3. 成交量放大
        if latest['volume_ratio'] > 1.2:
            score += 10
            reasons.append(f"成交量放大{latest['volume_ratio']:.2f}倍")

        # 4. 价格站上均线
        if latest['close'] > latest['ma5']:
            score += 10
            reasons.append("价格站上MA5")

        # 5. 动量向上
        if latest['mom'] > 0:
            score += 10
            reasons.append("动量指标向上")

        # 如果没有足够多的积极信号，不返回
        if len(reasons) < 2:
            return None

        # 设置入场价、止损价、目标价
        entry_price = latest['close']
        stop_loss = latest['low'] * 0.95
        target_price = entry_price * 1.06

        risk_level = self._determine_risk_level(abs(entry_price - stop_loss) / entry_price)

        return BuySignal(
            stock_code=stock_code,
            stock_name=stock_name,
            scan_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
            signal_type='潜在机会',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_score=min(score, 100),
            risk_level=risk_level,
            reasons=reasons,
            technical_indicators={
                'rsi': latest['rsi'],
                'macd_hist': latest['macdhist'],
                'volume_ratio': latest['volume_ratio']
            }
        )

    def _check_triangle_breakout(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[BuySignal]:
        """检查对称三角形突破买点"""
        if len(df) < 20:
            return None

        latest = df.iloc[-1]

        # 检查是否形成对称三角形
        # 高点越来越低，低点越来越高
        highs = df['high'].tail(10).values
        lows = df['low'].tail(10).values

        # 计算高点趋势（应该向下）
        high_trend = np.polyfit(range(len(highs)), highs, 1)[0]
        # 计算低点趋势（应该向上）
        low_trend = np.polyfit(range(len(lows)), lows, 1)[0]

        # 对称三角形条件：高点向下，低点向上
        if high_trend >= 0 or low_trend <= 0:
            return None

        # 检查成交量是否萎缩
        recent_volumes = df['volume'].tail(10).values
        volume_trend = np.polyfit(range(len(recent_volumes)), recent_volumes, 1)[0]
        if volume_trend >= 0:  # 成交量应该萎缩
            return None

        # 检查今天是否突破三角形上边
        triangle_upper = highs[0]  # 三角形上边（第一个高点）
        if latest['close'] <= triangle_upper:
            return None

        # 检查成交量是否放大
        if latest['volume'] < df['volume_ma5'].iloc[-1] * 1.3:
            return None

        # 检查RSI
        if latest['rsi'] > 75:
            return None

        # 计算信号评分
        score = 60  # 基础分

        # 高点向下趋势越明显，加分
        if high_trend < -0.5:
            score += 10
        elif high_trend < -0.2:
            score += 5

        # 低点向上趋势越明显，加分
        if low_trend > 0.5:
            score += 10
        elif low_trend > 0.2:
            score += 5

        # 成交量放大加分
        if latest['volume'] > df['volume_ma5'].iloc[-1] * 2:
            score += 10
        elif latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
            score += 5

        # RSI合理加分
        if 40 < latest['rsi'] < 65:
            score += 5

        score = min(score, 100)

        # 计算入场价、止损价、目标价
        entry_price = latest['close']
        stop_loss = lows[-1]  # 三角形下边
        target_price = entry_price + (triangle_upper - lows[-1])  # 三角形高度

        risk_level = self._determine_risk_level(abs(entry_price - stop_loss) / entry_price)

        reasons = [
            f"对称三角形突破，高点趋势{high_trend:.2f}，低点趋势{low_trend:.2f}",
            f"成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍",
            f"突破三角形上边{triangle_upper:.2f}"
        ]

        print(f"[对称三角形突破] {stock_code} - 信号评分: {score}")

        return BuySignal(
            stock_code=stock_code,
            stock_name=stock_name,
            scan_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
            signal_type='对称三角形突破',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_score=score,
            risk_level=risk_level,
            reasons=reasons,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                'macd_hist': latest['macdhist']
            }
        )

    def _check_expectation_gap(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[BuySignal]:
        """检查预期差买点（龙头核心模式）"""
        if len(df) < 10:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) >= 3 else None

        if prev2 is None:
            return None

        # 检查是否有分歧预期（前两天涨停或大涨）
        prev2_change = (prev2['close'] - prev2['open']) / prev2['open']
        if prev2_change < 0.05:  # 前两天涨幅小于5%，不算强势
            return None

        # 检查昨天是否分歧（下跌或涨幅很小）
        prev_change = (prev['close'] - prev['open']) / prev['open']
        if prev_change > 0.03:  # 昨天涨幅大于3%，不是分歧
            return None

        # 检查今天是否弱转强（上涨）
        latest_change = (latest['close'] - latest['open']) / latest['open']
        if latest_change <= 0:
            return None

        # 检查今天是否超预期（涨幅大于昨天）
        if latest_change <= abs(prev_change):
            return None

        # 检查成交量
        if latest['volume'] < df['volume_ma5'].iloc[-1] * 1.2:
            return None

        # 检查RSI
        if latest['rsi'] > 75:
            return None

        # 计算信号评分
        score = 65  # 基础分

        # 前两天越强势，加分
        if prev2_change > 0.09:  # 涨停
            score += 15
        elif prev2_change > 0.07:
            score += 10
        elif prev2_change > 0.05:
            score += 5

        # 昨天分歧越明显，加分
        if prev_change < -0.02:  # 下跌
            score += 10
        elif prev_change < 0:  # 小跌
            score += 5

        # 今天弱转强越明显，加分
        if latest_change > 0.05:
            score += 10
        elif latest_change > 0.03:
            score += 5

        score = min(score, 100)

        # 计算入场价、止损价、目标价
        entry_price = latest['close']
        stop_loss = prev['low']  # 昨天最低价
        target_price = entry_price * 1.12  # 12%目标（预期差模式目标更高）

        risk_level = self._determine_risk_level(abs(entry_price - stop_loss) / entry_price)

        reasons = [
            f"预期差买点，前日{prev2_change*100:.1f}%，昨日{prev_change*100:.1f}%，今日{latest_change*100:.1f}%",
            f"分歧预期+弱转强预期，今日超预期",
            f"成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍"
        ]

        print(f"[预期差买点] {stock_code} - 信号评分: {score}")

        return BuySignal(
            stock_code=stock_code,
            stock_name=stock_name,
            scan_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
            signal_type='预期差买点',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_score=score,
            risk_level=risk_level,
            reasons=reasons,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                'macd_hist': latest['macdhist']
            }
        )

    def _check_ice_point(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[BuySignal]:
        """检查冰点买点（衰竭性冰点）"""
        if len(df) < 20:
            return None

        latest = df.iloc[-1]

        # 检查是否经历普杀、缓和、再次普杀三个阶段
        # 第一阶段：普杀（前10天大幅下跌）
        first_stage = df['close'].tail(20).head(10)
        first_stage_decline = (first_stage.iloc[0] - first_stage.iloc[-1]) / first_stage.iloc[0]

        # 第二阶段：缓和（中间5天相对稳定）
        middle_stage = df['close'].tail(10).head(5)
        middle_stage_range = (middle_stage.max() - middle_stage.min()) / middle_stage.mean()

        # 第三阶段：再次普杀（最近5天再次下跌）
        last_stage = df['close'].tail(5)
        last_stage_decline = (last_stage.iloc[0] - last_stage.iloc[-1]) / last_stage.iloc[0]

        # 衰竭冰点条件
        if first_stage_decline < 0.10:  # 第一阶段跌幅不够
            return None
        if middle_stage_range > 0.05:  # 第二阶段波动太大
            return None
        if last_stage_decline < 0.05:  # 第三阶段跌幅不够
            return None

        # 检查今天是否止跌
        if latest['close'] < latest['open']:  # 今天还是阴线
            return None

        # 检查成交量
        if latest['volume'] < df['volume_ma5'].iloc[-1]:
            return None

        # 检查RSI（应该超卖）
        if latest['rsi'] > 40:
            return None

        # 计算信号评分
        score = 55  # 基础分

        # 第一阶段跌幅越大，加分
        if first_stage_decline < -0.20:
            score += 15
        elif first_stage_decline < -0.15:
            score += 10
        elif first_stage_decline < -0.10:
            score += 5

        # 第三阶段跌幅越大，加分
        if last_stage_decline < -0.10:
            score += 15
        elif last_stage_decline < -0.07:
            score += 10
        elif last_stage_decline < -0.05:
            score += 5

        # RSI越低，加分
        if latest['rsi'] < 25:
            score += 15
        elif latest['rsi'] < 30:
            score += 10
        elif latest['rsi'] < 35:
            score += 5

        score = min(score, 100)

        # 计算入场价、止损价、目标价
        entry_price = latest['close']
        stop_loss = df['low'].tail(20).min()  # 20天最低价
        target_price = entry_price * 1.15  # 15%目标（冰点反弹目标较高）

        risk_level = self._determine_risk_level(abs(entry_price - stop_loss) / entry_price)

        reasons = [
            f"衰竭性冰点，第一阶段下跌{abs(first_stage_decline)*100:.1f}%",
            f"第三阶段再次下跌{abs(last_stage_decline)*100:.1f}%，RSI={latest['rsi']:.1f}",
            f"今日止跌，博弈否极泰来"
        ]

        print(f"[冰点买点] {stock_code} - 信号评分: {score}")

        return BuySignal(
            stock_code=stock_code,
            stock_name=stock_name,
            scan_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
            signal_type='冰点买点',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_score=score,
            risk_level=risk_level,
            reasons=reasons,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                'macd_hist': latest['macdhist']
            }
        )

    def _determine_risk_level(self, risk_ratio: float) -> str:
        """确定风险等级"""
        if risk_ratio <= 0.05:
            return '低'
        elif risk_ratio <= 0.08:
            return '中'
        else:
            return '高'

    def get_top_signals(self, count: int = 10) -> List[BuySignal]:
        """获取评分最高的买点信号"""
        all_signals = self.scan_buy_signals()
        return all_signals[:count]