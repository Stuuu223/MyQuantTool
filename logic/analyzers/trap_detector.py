"""
诱多陷阱检测器
识别机构的"诱多"操作，包括：
1. 单日大额吸筹 + 隔日反手卖 = 诱多
2. 长期流出 + 单日巨量流入 = 游资突袭
3. 超大单主导 + 散户恐慌 = 对倒风险
"""
from typing import List, Dict, Any, Optional
from datetime import datetime


class TrapDetector:
    """
    诱多陷阱检测器

    识别模式:
    1. PUMP_AND_DUMP: 单日大额吸筹 + 隔日反手卖
    2. HOT_MONEY_RAID: 长期流出 + 单日巨量流入（游资突袭）
    3. SELF_TRADING_RISK: 超大单占比过高（对倒风险）
    """

    def __init__(self):
        """初始化检测器"""
        self.detected_traps = []

    def _is_cross_non_trading_day(self, date1: str, date2: str) -> bool:
        """
        检查两个日期之间是否跨越了非交易日（周末或假期）

        Args:
            date1: 日期字符串，格式 'YYYY-MM-DD'
            date2: 日期字符串，格式 'YYYY-MM-DD'

        Returns:
            True 如果跨越了非交易日，False 否则
        """
        from datetime import datetime

        try:
            dt1 = datetime.strptime(date1, '%Y-%m-%d')
            dt2 = datetime.strptime(date2, '%Y-%m-%d')

            # 确保日期顺序
            if dt1 > dt2:
                dt1, dt2 = dt2, dt1

            # 计算自然日间隔
            day_diff = (dt2 - dt1).days

            # 如果间隔 > 1，说明跨越了周末或假期
            # 例如：周五到周一间隔3天，跨越了周末
            return day_diff > 1

        except Exception as e:
            # 如果日期解析失败，保守处理，假设没有跨越
            return False

    def detect(self, stock_code: str, days: int = 30) -> Dict[str, Any]:
        """
        统一入口：检测股票的诱多陷阱

        Args:
            stock_code: 股票代码（6位）
            days: 分析天数（默认30天）

        Returns:
            检测结果，格式：
            {
                'signals': List[Dict],  # 诱多信号列表
                'detected_traps': List[Dict],  # 检测到的陷阱
                'trap_count': int,  # 陷阱数量
                'highest_severity': float,  # 最高严重程度
                'highest_risk_level': str,  # 最高风险等级
                'total_outflow': float,  # 累计流出
                'comprehensive_risk_score': float,  # 综合风险评分
                'risk_assessment': str,  # 风险评估
                'scan_time': str  # 扫描时间
            }
        """
        try:
            # 延迟导入，避免循环依赖
            from logic.data_providers.fund_flow_analyzer import FundFlowAnalyzer

            # 初始化资金流向分析器
            analyzer = FundFlowAnalyzer(enable_cache=True)

            # 获取资金流向数据
            fund_flow_data = analyzer.get_fund_flow(stock_code, days=days)

            if "error" in fund_flow_data:
                return {
                    'signals': [],
                    'detected_traps': [],
                    'trap_count': 0,
                    'highest_severity': 0,
                    'highest_risk_level': 'NONE',
                    'total_outflow': 0,
                    'comprehensive_risk_score': 0,
                    'risk_assessment': f"数据获取失败: {fund_flow_data['error']}",
                    'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            # 提取每日数据
            daily_data = fund_flow_data.get('records', [])

            if not daily_data:
                return {
                    'signals': [],
                    'detected_traps': [],
                    'trap_count': 0,
                    'highest_severity': 0,
                    'highest_risk_level': 'NONE',
                    'total_outflow': 0,
                    'comprehensive_risk_score': 0,
                    'risk_assessment': '无资金流向数据',
                    'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            # 转换数据格式（从 fund_flow_analyzer 格式转换为 trap_detector 格式）
            converted_data = []
            for record in daily_data:
                date_value = record.get('date', '')
                # 如果是 datetime.date 类型，转换为字符串
                if hasattr(date_value, 'strftime'):
                    date_value = date_value.strftime('%Y-%m-%d')
                elif not isinstance(date_value, str):
                    date_value = str(date_value)

                converted_data.append({
                    'date': date_value,
                    'institution': record.get('super_large_net', 0) + record.get('large_net', 0),  # 机构资金
                    'super_large': record.get('super_large_net', 0),
                    'large': record.get('large_net', 0),
                    'medium': record.get('medium_net', 0),
                    'small': record.get('small_net', 0),
                    'retail': record.get('medium_net', 0) + record.get('small_net', 0)  # 散户资金
                })

            # 计算滚动趋势
            for i in range(len(converted_data)):
                # 5日滚动
                start_idx = max(0, i - 4)
                flow_5d = sum(d['institution'] for d in converted_data[start_idx:i+1])
                converted_data[i]['flow_5d_net'] = flow_5d

                # 10日滚动
                start_idx = max(0, i - 9)
                flow_10d = sum(d['institution'] for d in converted_data[start_idx:i+1])
                converted_data[i]['flow_10d_net'] = flow_10d

            # 调用综合扫描
            result = self.comprehensive_trap_scan(converted_data)

            # 转换信号格式（从 detected_traps 转换为 signals）
            signals = []
            for trap in result.get('detected_traps', []):
                # 兼容两种字段名：trap_type 或 type
                trap_type = trap.get('trap_type') or trap.get('type', 'UNKNOWN')
                # 转换为中文信号名称，便于 _calculate_risk_score 识别
                if trap_type == 'PUMP_AND_DUMP':
                    signals.append('单日暴量+隔日反手')
                elif trap_type == 'HOT_MONEY_RAID':
                    signals.append('游资突袭')
                elif trap_type == 'SELF_TRADING_RISK':
                    signals.append('长期流出+单日巨量')
                else:
                    # 保留原始类型，同时添加详细信息
                    signals.append({
                        'type': trap_type,
                        'severity': trap.get('confidence', 0),
                        'date': trap.get('date', ''),
                        'description': trap.get('description', '')
                    })

            result['signals'] = signals

            return result

        except Exception as e:
            return {
                'signals': [],
                'detected_traps': [],
                'trap_count': 0,
                'highest_severity': 0,
                'highest_risk_level': 'NONE',
                'total_outflow': 0,
                'comprehensive_risk_score': 0,
                'risk_assessment': f"检测失败: {str(e)}",
                'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    def detect_pump_and_dump(self, daily_data: List[Dict[str, Any]], max_traps: int = 5, strict_mode: bool = True) -> Dict[str, Any]:
        """
        检测"吸筹-反手卖"诱多陷阱

        严格模式（strict_mode=True）：
        - 吸筹 >= 1000万
        - 隔日卖出 >= 当日吸筹的 80%（必须反手卖）
        - 5日/10日滚动仍在流出（持续流出）
        - 排除小额试单

        普通模式（strict_mode=False）：
        - 吸筹 >= 5000万
        - 隔日卖出 >= 2500万
        - 3个特征至少满足2个

        时间衰减权重：
        - 最近30天：权重 100%
        - 30-60天：权重 70%
        - 60+天：权重 30%

        Args:
            daily_data: 每日资金流向数据
            max_traps: 最多返回的陷阱数量（默认5个）
            strict_mode: 是否使用严格模式（默认True）

        Returns:
            检测结果字典
        """
        if len(daily_data) < 2:
            return {
                'detected': False,
                'detected_traps': [],
                'trap_count': 0,
                'reason': '数据不足，至少需要2天'
            }

        detected_traps = []

        # 计算今天的日期
        from datetime import datetime
        today_date = daily_data[-1]['date']
        today = datetime.strptime(today_date, '%Y-%m-%d')

        # 扫描所有相邻的两天，检测所有诱多模式
        for i in range(len(daily_data) - 1):
            prev_day = daily_data[i]
            curr_day = daily_data[i + 1]

            inflow_amount = prev_day.get('institution', 0)
            dump_amount = curr_day.get('institution', 0)

            # 计算距今天数
            inflow_date = datetime.strptime(prev_day['date'], '%Y-%m-%d')
            days_ago = (today - inflow_date).days

            # ========== 严格模式 ==========
            if strict_mode:
                # 🔥 [Hotfix] 检查：如果 curr_day 是今天，跳过"隔日反手"判定
                # 因为"隔日"还没发生，不能判定是否反手
                if curr_day['date'] == today_date:
                    continue  # 今天的数据，不能判定"隔日反手"

                # 🔥 [Hotfix] 检查：如果跨越了非交易日（周末/假期），跳过"隔日反手"判定
                # 跨越周末/假期的资金流动不是"隔日反手"，是正常调仓
                if self._is_cross_non_trading_day(prev_day['date'], curr_day['date']):
                    continue  # 跨越非交易日，不能判定为"隔日反手"

                # 严格条件 1: 吸筹金额 >= 1000万
                if inflow_amount < 1000:
                    continue

                # 严格条件 2: 隔日卖出必须是流出
                if dump_amount >= 0:
                    continue

                # 严格条件 3: 反手卖比例 >= 80%
                dump_ratio = abs(dump_amount) / inflow_amount
                if dump_ratio < 0.80:
                    continue  # 没有反手卖，只是部分减仓

                # 严格条件 4: 5日/10日滚动仍在流出
                flow_5d = curr_day.get('flow_5d_net', 0)
                flow_10d = curr_day.get('flow_10d_net', 0)
                if flow_5d > 0 or flow_10d > 0:
                    continue  # 还在吸筹中，不是诱多

                # 计算时间衰减权重
                if days_ago > 60:
                    time_weight = 0.30
                elif days_ago > 30:
                    time_weight = 0.70
                else:
                    time_weight = 1.00

                # 计算严重程度（基于吸筹金额）
                if inflow_amount > 10000:
                    severity = "CRITICAL"
                elif inflow_amount > 5000:
                    severity = "HIGH"
                elif inflow_amount > 3000:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"

                # 计算置信度（基础0.7，乘以时间权重）
                confidence = 0.70 * time_weight
                if dump_ratio >= 1.0:
                    confidence += 0.15  # 完全反手卖
                if inflow_amount > 10000:
                    confidence += 0.05

                detected_traps.append({
                    'detected': True,
                    'type': 'PUMP_AND_DUMP',
                    'type_name': '诱多陷阱（吸筹-反手卖）',
                    'confidence': round(min(confidence, 0.95), 2),
                    'inflow_day': prev_day['date'],
                    'inflow_amount': inflow_amount,
                    'dump_day': curr_day['date'],
                    'dump_amount': dump_amount,
                    'dump_ratio': round(dump_ratio * 100, 2),  # 反手卖比例（百分比）
                    'price_change_prev': prev_day.get('pct_chg', 0),
                    'evidence': self._format_pump_dump_evidence(prev_day, curr_day),
                    'severity': severity,
                    'is_recent': days_ago <= 30,
                    'days_ago': days_ago,
                    'time_weight': time_weight
                })

            # ========== 普通模式（向后兼容）==========
            else:
                # 特征 1: 前一天大额吸筹（阈值5000万）
                big_inflow = prev_day.get('institution', 0) > 5000

                # 特征 2: 当天反手卖出（阈值-2500万）
                big_outflow = curr_day.get('institution', 0) < -2500

                # 特征 3: 前一天涨幅明显（阈值3%）
                price_surge = prev_day.get('pct_chg', 0) > 3.0

                # 综合判断（3个特征至少满足2个，但前两个特征必须至少满足1个）
                feature_count = sum([big_inflow, big_outflow, price_surge])
                has_volume_feature = big_inflow or big_outflow

                if feature_count >= 2 and has_volume_feature:
                    # 计算严重程度（基于吸筹金额）
                    if inflow_amount > 15000:
                        severity = "CRITICAL"
                    elif inflow_amount > 10000:
                        severity = "HIGH"
                    elif inflow_amount > 5000:
                        severity = "MEDIUM"
                    else:
                        severity = "LOW"

                    # 计算置信度
                    confidence = 0.60 + (feature_count * 0.10)
                    if big_inflow and big_outflow and price_surge:
                        confidence = 0.90
                    if inflow_amount > 10000:
                        confidence = min(confidence + 0.05, 0.95)

                    detected_traps.append({
                        'detected': True,
                        'type': 'PUMP_AND_DUMP',
                        'type_name': '诱多陷阱（吸筹-反手卖）',
                        'confidence': round(confidence, 2),
                        'inflow_day': prev_day['date'],
                        'inflow_amount': inflow_amount,
                        'dump_day': curr_day['date'],
                        'dump_amount': dump_amount,
                        'price_change_prev': prev_day.get('pct_chg', 0),
                        'evidence': self._format_pump_dump_evidence(prev_day, curr_day),
                        'severity': severity,
                        'is_recent': days_ago <= 30,
                        'days_ago': days_ago
                    })

        if detected_traps:
            # 按吸筹金额排序（从大到小）
            detected_traps.sort(key=lambda x: x['inflow_amount'], reverse=True)

            # 保留前 max_traps 个
            top_traps = detected_traps[:max_traps]

            # 风险总结
            recent_critical_traps = sum(1 for t in top_traps if t.get('severity') == 'CRITICAL' and t.get('is_recent', False))
            any_recent_trap = any(t.get('is_recent', False) for t in top_traps)

            risk_summary = {
                'total_traps': len(detected_traps),
                'critical_traps': sum(1 for t in detected_traps if t.get('severity') == 'CRITICAL'),
                'recent_traps': sum(1 for t in detected_traps if t.get('is_recent', False)),
                'max_inflow': max(t['inflow_amount'] for t in detected_traps),
                'recommendation': 'AVOID - 检测到诱多陷阱，建议回避' if (recent_critical_traps > 0 or any_recent_trap) else 'WAIT_AND_WATCH'
            }

            return {
                'detected': True,
                'trap_count': len(top_traps),
                'detected_traps': top_traps,
                'risk_summary': risk_summary,
                'highest_severity': top_traps[0]['severity'] if top_traps else None,
                'highest_risk_level': top_traps[0]['severity'] if top_traps else None
            }

        return {
            'detected': False,
            'detected_traps': [],
            'trap_count': 0,
            'reason': '未检测到诱多模式'
        }

    def detect_hot_money_raid(self, daily_data: List[Dict[str, Any]], window: int = 30) -> Dict[str, Any]:
        """
        检测"游资突袭"模式

        模式特征:
        - 前 window-1 天累计净流出 > -2000万（调整阈值）
        - 最后一天单日巨量流入 > 2000万（调整阈值）
        - 填坑率 > 30%（单日流入 / 前期累计流出的绝对值，调整阈值）

        Args:
            daily_data: 每日资金流向数据
            window: 检测窗口大小（默认30天）

        Returns:
            检测结果字典
        """
        if len(daily_data) < window:
            return {'detected': False, 'reason': f'数据不足，至少需要{window}天'}

        # 获取最近 window 天的数据
        recent = daily_data[-window:]
        latest = daily_data[-1]

        # 计算前 window-1 天的累计流向
        cumulative_before = sum(d.get('institution', 0) for d in recent[:-1])

        # 最后一天的流入
        latest_inflow = latest.get('institution', 0)

        # 特征判断（调整阈值）
        long_term_outflow = cumulative_before < -2000
        single_day_inflow = latest_inflow > 2000

        if long_term_outflow and single_day_inflow:
            # 计算"填坑率"
            fill_ratio = latest_inflow / abs(cumulative_before)
            high_fill_ratio = fill_ratio > 0.3  # 调整到30%

            if high_fill_ratio:
                confidence = 0.65
                if fill_ratio > 0.6:
                    confidence = 0.80
                elif fill_ratio > 0.8:
                    confidence = 0.90
                elif fill_ratio > 1.0:
                    confidence = 0.95  # 完全填坑甚至超额

                # 如果单日流入特别大（> 5000万），置信度更高
                if latest_inflow > 5000:
                    confidence = min(confidence + 0.03, 0.98)

                return {
                    'detected': True,
                    'type': 'HOT_MONEY_RAID',
                    'type_name': '游资突袭',
                    'confidence': round(confidence, 2),
                    'window_days': window,
                    'cumulative_outflow': round(cumulative_before, 2),
                    'single_day_inflow': latest_inflow,
                    'fill_ratio': round(fill_ratio, 4),
                    'evidence': self._format_hot_money_evidence(cumulative_before, latest_inflow, fill_ratio, window),
                    'risk_level': 'HIGH' if fill_ratio < 0.6 else 'CRITICAL'
                }

        return {'detected': False, 'reason': '未检测到游资突袭模式'}

    def detect_self_trading(self, daily_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        检测"对倒"风险

        模式特征:
        - 超大单占比过高（> 70%）
        - 总流向金额较大（> 3000万）
        - 散户资金流向与机构相反（可能被对倒）

        Args:
            daily_data: 每日资金流向数据

        Returns:
            检测结果字典
        """
        if not daily_data:
            return {'detected': False, 'reason': '数据为空'}

        latest = daily_data[-1]

        # 获取超大单数据
        super_large = abs(latest.get('super_large', 0))
        total_flow = abs(latest.get('institution', 0))

        # 特征判断
        if total_flow > 3000:
            super_large_ratio = super_large / total_flow if total_flow > 0 else 0

            if super_large_ratio > 0.7:
                confidence = 0.60 + (super_large_ratio - 0.7) * 1.5  # 0.7 -> 0.6, 0.8 -> 0.75

                # 检查散户流向是否与机构相反
                retail_flow = latest.get('retail', 0)
                institution_flow = latest.get('institution', 0)

                opposite_direction = (retail_flow > 0 and institution_flow < 0) or \
                                   (retail_flow < 0 and institution_flow > 0)

                if opposite_direction:
                    confidence += 0.10

                confidence = min(confidence, 0.85)

                return {
                    'detected': True,
                    'type': 'SELF_TRADING_RISK',
                    'type_name': '对倒风险',
                    'confidence': round(confidence, 2),
                    'super_large_amount': super_large,
                    'total_flow': total_flow,
                    'super_large_ratio': round(super_large_ratio, 4),
                    'retail_flow': retail_flow,
                    'institution_flow': institution_flow,
                    'opposite_direction': opposite_direction,
                    'evidence': self._format_self_trading_evidence(super_large, total_flow, super_large_ratio),
                    'risk_level': 'HIGH' if confidence < 0.75 else 'CRITICAL'
                }

        return {'detected': False, 'reason': '未检测到对倒风险'}

    def comprehensive_trap_scan(self, daily_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        综合扫描所有陷阱模式（使用严格模式）

        Args:
            daily_data: 每日资金流向数据

        Returns:
            综合检测结果
        """
        self.detected_traps = []

        # 检测 1: 诱多陷阱（使用严格模式）
        pump_dump = self.detect_pump_and_dump(daily_data, strict_mode=True)
        if pump_dump['detected']:
            self.detected_traps.extend(pump_dump['detected_traps'])

        # 检测 2: 游资突袭
        hot_money = self.detect_hot_money_raid(daily_data)
        if hot_money['detected']:
            self.detected_traps.append(hot_money)

        # 检测 3: 对倒风险
        self_trade = self.detect_self_trading(daily_data)
        if self_trade['detected']:
            self.detected_traps.append(self_trade)

        # 计算累计流出（用于风险评分）
        total_outflow = sum(d.get('institution', 0) for d in daily_data)

        # 获取当前滚动趋势
        latest = daily_data[-1]
        flow_5d = latest.get('flow_5d_net', 0)
        flow_10d = latest.get('flow_10d_net', 0)

        # 计算综合风险评分（考虑当前趋势）
        risk_score = self._calculate_comprehensive_risk(total_outflow, flow_5d, flow_10d)

        return {
            'detected_traps': self.detected_traps,
            'trap_count': len(self.detected_traps),
            'highest_severity': max([t.get('confidence', 0) for t in self.detected_traps], default=0),
            'highest_risk_level': self._get_highest_risk_level(),
            'total_outflow': round(total_outflow, 2),
            'comprehensive_risk_score': risk_score,
            'risk_assessment': self._get_risk_assessment(risk_score),
            'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _calculate_comprehensive_risk(self, total_outflow: float = 0, flow_5d: float = 0, flow_10d: float = 0) -> float:
        """
        计算综合风险评分（0-1）

        评分规则（最终优化版）：
        - 优先考虑当前趋势（5日/10日滚动）
        - 如果当前在吸筹（5日>0且10日>0），大幅降低风险
        - 只考虑最近30天内的诱多
        - CRITICAL级别: 置信度 * 0.3（大幅降低）
        - HIGH级别: 置信度 * 0.2
        - MEDIUM级别: 置信度 * 0.1

        Args:
            total_outflow: 90天累计流出
            flow_5d: 5日滚动净流入
            flow_10d: 10日滚动净流入
        """
        if not self.detected_traps:
            return 0.0

        # 只考虑最近30天内的诱多
        recent_traps = [t for t in self.detected_traps if t.get('is_recent', False)]

        # 如果没有最近诱多，风险很低
        if not recent_traps:
            return 0.0

        base_risk = 0.0

        for trap in recent_traps:
            confidence = trap.get('confidence', 0)
            severity = trap.get('severity', 'LOW')

            # 根据严重程度计算权重（大幅降低）
            if severity == 'CRITICAL':
                weight = 0.3  # 从 0.5 降低到 0.3
            elif severity == 'HIGH':
                weight = 0.2  # 从 0.3 降低到 0.2
            elif severity == 'MEDIUM':
                weight = 0.1  # 从 0.2 降低到 0.1
            else:
                weight = 0.05

            base_risk += confidence * weight

        # 陷阱数量加成（大幅降低）
        trap_count_bonus = (len(recent_traps) - 1) * 0.05  # 从 0.10 降低到 0.05

        # 累计流出加成（几乎不考虑）
        if total_outflow < -100000:  # 10亿流出
            outflow_bonus = min(abs(total_outflow) / 500000, 0.02)  # 最多加 0.02
        else:
            outflow_bonus = 0

        # 当前趋势调整（关键！大幅提高权重）
        if flow_5d > 0 and flow_10d > 0:
            # 正在吸筹，大幅降低风险
            trend_adjustment = -0.40  # 从 -0.30 提高到 -0.40
        elif flow_5d > 0:
            # 5日流入，适度降低风险
            trend_adjustment = -0.20  # 从 -0.15 提高到 -0.20
        elif flow_5d < -10000:
            # 5日大幅流出，增加风险
            trend_adjustment = 0.30
        elif flow_5d < 0:
            # 5日小幅流出，轻微增加风险
            trend_adjustment = 0.15
        else:
            trend_adjustment = 0

        # 限制在 0-1
        final_risk = max(0.0, min(1.0, base_risk + trap_count_bonus + outflow_bonus + trend_adjustment))

        return final_risk

    def _get_highest_risk_level(self) -> str:
        """获取最高风险等级"""
        if not self.detected_traps:
            return 'LOW'

        levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        level_order = {level: i for i, level in enumerate(levels)}

        highest_level = max(
            [t.get('risk_level', 'LOW') for t in self.detected_traps],
            key=lambda x: level_order.get(x, 0)
        )

        return highest_level

    def _get_risk_assessment(self, risk_score: float) -> str:
        """获取风险评估"""
        if risk_score >= 0.8:
            return 'CRITICAL - 高风险诱多陷阱，建议立即回避'
        elif risk_score >= 0.6:
            return 'HIGH - 高风险，建议谨慎观察'
        elif risk_score >= 0.4:
            return 'MEDIUM - 中等风险，可小仓位试探'
        else:
            return 'LOW - 低风险，可正常参与'

    def _format_pump_dump_evidence(self, prev_day: Dict, curr_day: Dict) -> str:
        """格式化诱多证据"""
        return (f"{prev_day['date']} 机构净流入 {prev_day.get('institution', 0):.2f}万"
                f"（涨幅 {prev_day.get('pct_chg', 0):.2f}%），"
                f"{curr_day['date']} 反手卖出 {curr_day.get('institution', 0):.2f}万")

    def _format_hot_money_evidence(self, cumulative_outflow: float,
                                   latest_inflow: float,
                                   fill_ratio: float,
                                   window: int) -> str:
        """格式化游资突袭证据"""
        return (f"前{window-1}天累计净流出 {cumulative_outflow:.2f}万，"
                f"今日单日流入 {latest_inflow:.2f}万，"
                f"填坑率 {fill_ratio*100:.1f}%")

    def _format_self_trading_evidence(self, super_large: float,
                                      total_flow: float,
                                      ratio: float) -> str:
        """格式化对倒风险证据"""
        return (f"超大单占比 {ratio*100:.1f}%"
                f"（{super_large:.2f}万 / {total_flow:.2f}万），"
                f"可能存在对倒操作")


# 便捷函数
def detect_traps(daily_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """便捷函数：检测所有陷阱"""
    detector = TrapDetector()
    return detector.comprehensive_trap_scan(daily_data)


if __name__ == "__main__":
    # 测试代码
    import json

    print("=" * 80)
    print("诱多陷阱检测器测试")
    print("=" * 80)

    # 模拟数据：诱多陷阱
    test_pump_dump = [
        {'date': '2026-01-28', 'institution': 6000, 'pct_chg': 3.5, 'super_large': 4500, 'large': 1500, 'retail': -6000},
        {'date': '2026-01-29', 'institution': -3000, 'pct_chg': -1.2, 'super_large': -2500, 'large': -500, 'retail': 3000}
    ]

    print("\n测试1: 诱多陷阱（吸筹-反手卖）")
    detector = TrapDetector()
    result = detector.detect_pump_and_dump(test_pump_dump)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 模拟数据：游资突袭
    test_hot_money = []
    for i in range(29):
        test_hot_money.append({
            'date': f'2026-01-{i+1:02d}',
            'institution': -200 - i * 10,
            'super_large': -150 - i * 5,
            'retail': 200 + i * 10
        })
    test_hot_money.append({
        'date': '2026-01-30',
        'institution': 5000,
        'super_large': 4000,
        'retail': -5000
    })

    print("\n测试2: 游资突袭")
    result = detector.detect_hot_money_raid(test_hot_money)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 模拟数据：对倒风险
    test_self_trade = [
        {'date': '2026-01-30', 'institution': 4000, 'super_large': 3200, 'large': 800, 'retail': -4000}
    ]

    print("\n测试3: 对倒风险")
    result = detector.detect_self_trading(test_self_trade)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 综合扫描
    print("\n测试4: 综合扫描")
    test_combined = test_pump_dump + test_hot_money + test_self_trade
    result = detector.comprehensive_trap_scan(test_combined)
    print(f"检测到 {result['trap_count']} 个陷阱")
    print(f"综合风险评分: {result['comprehensive_risk_score']:.2f}")
    print(f"风险评估: {result['risk_assessment']}")

    print("\n✅ 测试完成")
