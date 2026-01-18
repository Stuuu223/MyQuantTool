"""
V14 AutoReviewer - 自动化案例收集与复盘系统

功能：
1. "打脸"案例集：系统评分>85但次日跌幅>3%
2. "踏空"案例集：系统评分<60但今日涨停
3. "救命"案例集：被事实熔断按住但次日大跌
4. V14.3 模式捕获（Pattern Hunter）：分析踏空案例的模式特征

使用：
每天15:30收盘后运行，生成《每日异常交易报告》
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from collections import Counter
from logic.data_manager import DataManager
from logic.signal_generator import get_signal_generator_v13
from logic.signal_history import get_signal_history_manager
from logic.logger import get_logger

logger = get_logger(__name__)


class AutoReviewer:
    """
    自动案例收集器
    """
    
    def __init__(self, data_manager: DataManager = None):
        """
        初始化
        
        Args:
            data_manager: 数据管理器实例
        """
        self.dm = data_manager or DataManager()
        self.sg = get_signal_generator_v13()
        self.shm = get_signal_history_manager()
        
        # 创建案例存储目录
        self.base_dir = Path("data/review_cases")
        self.slap_dir = self.base_dir / "false_positives"  # 打脸案例
        self.missed_dir = self.base_dir / "missed_opportunities"  # 踏空案例
        self.lifesaver_dir = self.base_dir / "lifesavers"  # 救命案例
        
        for dir_path in [self.base_dir, self.slap_dir, self.missed_dir, self.lifesaver_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def collect_slap_cases(self, date: str = None) -> List[Dict]:
        """
        收集"打脸"案例：系统评分>85但次日跌幅>3%
        
        Args:
            date: 日期字符串，格式YYYY-MM-DD，默认为昨天
        
        Returns:
            案例列表
        """
        if date is None:
            yesterday = datetime.now() - timedelta(days=1)
            date = yesterday.strftime("%Y-%m-%d")
        
        logger.info(f"正在收集 {date} 的打脸案例...")
        
        # TODO: 从数据库或Redis获取当天的BUY信号列表
        # 这里需要实现历史信号存储功能
        buy_signals = self._get_historical_buy_signals(date)
        
        slap_cases = []
        
        for signal in buy_signals:
            stock_code = signal['stock_code']
            score = signal['final_score']
            
            # 获取今日数据
            today_data = self.dm.get_realtime_data(stock_code)
            
            if today_data and 'change_percent' in today_data:
                change_pct = today_data['change_percent']
                
                # 打脸条件：系统评分>85但跌幅>3%
                if score > 85 and change_pct < -3:
                    case = {
                        'stock_code': stock_code,
                        'date': date,
                        'system_score': score,
                        'today_change': change_pct,
                        'signal_type': signal['signal'],
                        'reason': signal['reason'],
                        'fact_veto': signal.get('fact_veto', False)
                    }
                    slap_cases.append(case)
                    logger.warning(f"打脸案例: {stock_code} 评分{score} 今日跌幅{change_pct:.2f}%")
        
        # 保存案例
        if slap_cases:
            self._save_cases(slap_cases, self.slap_dir, f"slap_{date}.csv")
            logger.info(f"保存 {len(slap_cases)} 个打脸案例")
        
        return slap_cases
    
    def collect_missed_opportunities(self, date: str = None) -> List[Dict]:
        """
        收集"踏空"案例：系统评分<60但今日涨停
        
        Args:
            date: 日期字符串，格式YYYY-MM-DD，默认为今天
        
        Returns:
            案例列表
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"正在收集 {date} 的踏空案例...")
        
        # 获取今日涨停板名单
        limit_up_stocks = self._get_limit_up_stocks(date)
        
        missed_cases = []
        
        for stock_code in limit_up_stocks:
            # 获取历史数据
            df = self.dm.get_history_data(symbol=stock_code)
            
            if df is None or len(df) < 2:
                continue
            
            # 获取昨天的数据
            yesterday_data = df.iloc[-2]
            
            # 获取资金流向
            capital_flow, market_cap = self.sg.get_capital_flow(stock_code, self.dm)
            
            # 获取趋势
            trend = self.sg.get_trend_status(df.iloc[:-1])
            
            # 计算系统评分（使用默认AI分数75）
            result = self.sg.calculate_final_signal(
                stock_code=stock_code,
                ai_narrative_score=75,
                capital_flow_data=capital_flow,
                trend_status=trend,
                circulating_market_cap=market_cap
            )
            
            # 踏空条件：系统评分<60但今日涨停
            if result['final_score'] < 60:
                case = {
                    'stock_code': stock_code,
                    'date': date,
                    'system_score': result['final_score'],
                    'today_status': 'LIMIT_UP',
                    'signal': result['signal'],
                    'reason': result['reason'],
                    'fact_veto': result.get('fact_veto', False),
                    'capital_flow': capital_flow,
                    'trend': trend
                }
                missed_cases.append(case)
                logger.warning(f"踏空案例: {stock_code} 评分{result['final_score']:.1f} 今日涨停")
        
        # 保存案例
        if missed_cases:
            self._save_cases(missed_cases, self.missed_dir, f"missed_{date}.csv")
            logger.info(f"保存 {len(missed_cases)} 个踏空案例")
        
        return missed_cases
    
    def collect_lifesaver_cases(self, date: str = None) -> List[Dict]:
        """
        收集"救命"案例：被事实熔断按住但次日大跌
        
        Args:
            date: 日期字符串，格式YYYY-MM-DD，默认为今天
        
        Returns:
            案例列表
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"正在收集 {date} 的救命案例...")
        
        # TODO: 从数据库获取昨天被事实熔断的股票列表
        vetoed_stocks = self._get_fact_vetoed_stocks(date)
        
        lifesaver_cases = []
        
        for stock_data in vetoed_stocks:
            stock_code = stock_data['stock_code']
            ai_score = stock_data['ai_score']
            veto_reason = stock_data['veto_reason']
            
            # 获取今日数据
            today_data = self.dm.get_realtime_data(stock_code)
            
            if today_data and 'change_percent' in today_data:
                change_pct = today_data['change_percent']
                
                # 救命条件：被事实熔断且今日跌幅>3%
                if change_pct < -3:
                    case = {
                        'stock_code': stock_code,
                        'date': date,
                        'ai_score': ai_score,
                        'veto_reason': veto_reason,
                        'today_change': change_pct,
                        'saved_loss': abs(change_pct)  # 避免的损失
                    }
                    lifesaver_cases.append(case)
                    logger.info(f"救命案例: {stock_code} AI评分{ai_score} 被熔断({veto_reason}) 今日跌幅{change_pct:.2f}%")
        
        # 保存案例
        if lifesaver_cases:
            self._save_cases(lifesaver_cases, self.lifesaver_dir, f"lifesaver_{date}.csv")
            logger.info(f"保存 {len(lifesaver_cases)} 个救命案例")
        
        return lifesaver_cases
    
    def generate_daily_report(self, date: str = None) -> str:
        """
        生成每日异常交易报告
        
        Args:
            date: 日期字符串，格式YYYY-MM-DD，默认为今天
        
        Returns:
            报告文本
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"正在生成 {date} 的每日异常交易报告...")
        
        # 收集三类案例
        slap_cases = self.collect_slap_cases(date)
        missed_cases = self.collect_missed_opportunities(date)
        lifesaver_cases = self.collect_lifesaver_cases(date)
        
        # 生成报告
        report = f"""
# 每日异常交易报告
日期: {date}
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 📊 统计摘要
- 打脸案例: {len(slap_cases)} 个
- 踏空案例: {len(missed_cases)} 个
- 救命案例: {len(lifesaver_cases)} 个

---

## 🚨 打脸案例（系统评分>85但次日跌幅>3%）
"""
        
        if slap_cases:
            for i, case in enumerate(slap_cases, 1):
                report += f"""
### 案例 {i}: {case['stock_code']}
- 系统评分: {case['system_score']:.1f}
- 今日跌幅: {case['today_change']:.2f}%
- 信号类型: {case['signal']}
- 原因: {case['reason']}
- 事实熔断: {case['fact_veto']}

"""
        else:
            report += "\n无打脸案例 ✅\n"
        
        report += """
---

## 💨 踏空案例（系统评分<60但今日涨停）
"""
        
        if missed_cases:
            for i, case in enumerate(missed_cases, 1):
                report += f"""
### 案例 {i}: {case['stock_code']}
- 系统评分: {case['system_score']:.1f}
- 今日状态: {case['today_status']}
- 信号: {case['signal']}
- 原因: {case['reason']}
- 事实熔断: {case['fact_veto']}
- 资金流向: {case['capital_flow']/10000:.0f}万
- 趋势: {case['trend']}

"""
        else:
            report += "\n无踏空案例 ✅\n"
        
        report += """
---

## 🛡️ 救命案例（被事实熔断按住但次日大跌）
"""
        
        if lifesaver_cases:
            total_saved = sum(case['saved_loss'] for case in lifesaver_cases)
            report += f"\n**累计避免损失: {total_saved:.2f}%**\n\n"
            
            for i, case in enumerate(lifesaver_cases, 1):
                report += f"""
### 案例 {i}: {case['stock_code']}
- AI评分: {case['ai_score']}
- 熔断原因: {case['veto_reason']}
- 今日跌幅: {case['today_change']:.2f}%
- 避免损失: {case['saved_loss']:.2f}%

"""
        else:
            report += "\n无救命案例\n"
        
        report += f"""

---

*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
*V14 AutoReviewer v1.0*
"""
        
        # 保存报告
        report_file = self.base_dir / f"daily_report_{date}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"报告已保存到 {report_file}")
        
        return report
    
    def _get_historical_buy_signals(self, date: str) -> List[Dict]:
        """
        获取历史BUY信号列表
        """
        buy_signals = self.shm.get_buy_signals_by_date(date)
        logger.info(f"从历史记录获取到 {len(buy_signals)} 个BUY信号")
        return buy_signals
    
    def _get_limit_up_stocks(self, date: str) -> List[str]:
        """
        获取涨停板股票列表
        
        Args:
            date: 日期字符串，格式YYYY-MM-DD
        
        Returns:
            涨停板股票代码列表
        """
        try:
            import akshare as ak
            import pandas as pd
            
            # 格式转换：2026-01-18 -> 20260118
            date_str = date.replace('-', '')
            
            logger.info(f"正在获取 {date} 的涨停板数据...")
            
            # 获取涨停板数据
            df = ak.stock_zt_pool_em(date=date_str)
            
            if df is not None and not df.empty:
                # 提取股票代码列表
                stock_codes = df['代码'].tolist()
                logger.info(f"成功获取 {len(stock_codes)} 只涨停板股票")
                return stock_codes
            else:
                logger.warning(f"{date} 无涨停板数据")
                return []
                
        except ImportError:
            logger.error("akshare模块未安装，无法获取涨停板数据")
            return []
        except Exception as e:
            logger.error(f"获取涨停板数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_fact_vetoed_stocks(self, date: str) -> List[Dict]:
        """
        获取被事实熔断的股票列表
        """
        vetoed_signals = self.shm.get_fact_vetoed_signals(date)
        
        # 转换格式
        result = []
        for signal in vetoed_signals:
            result.append({
                'stock_code': signal['stock_code'],
                'ai_score': signal['ai_score'],
                'veto_reason': signal['reason']
            })
        
        logger.info(f"从历史记录获取到 {len(result)} 个被熔断的信号")
        return result
    
    def _save_cases(self, cases: List[Dict], directory: Path, filename: str):
        """
        保存案例到CSV文件
        
        Args:
            cases: 案例列表
            directory: 目录路径
            filename: 文件名
        """
        if not cases:
            return
        
        df = pd.DataFrame(cases)
        filepath = directory / filename
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"案例已保存到 {filepath}")
    
    def analyze_missed_patterns(self, days: int = 5) -> Dict:
        """
        V14.3 模式捕获：分析踏空案例的模式特征
        
        分析维度：
        1. 市值分布：微盘(<20亿)、中小盘(20-100亿)、大盘(>100亿)
        2. 行业分布：Top 3 热门行业
        3. 量价特征：平均换手率和量比
        4. 时间分布：首板时间分布
        
        Args:
            days: 分析过去N天的数据
        
        Returns:
            分析结果字典，包含模式发现和优化建议
        """
        logger.info(f"开始分析过去 {days} 天的踏空案例模式...")
        
        # 1. 读取过去N天的踏空案例
        missed_cases = self._load_missed_cases(days)
        
        # 初始化默认结果结构
        default_result = {
            'total_cases': 0,
            'date_range': {
                'start': datetime.now().strftime("%Y-%m-%d"),
                'end': datetime.now().strftime("%Y-%m-%d")
            },
            'market_cap_distribution': {
                'micro_cap': {'count': 0, 'percentage': 0, 'avg_cap': 0},
                'small_mid_cap': {'count': 0, 'percentage': 0, 'avg_cap': 0},
                'large_cap': {'count': 0, 'percentage': 0, 'avg_cap': 0}
            },
            'industry_distribution': {
                'top_3': [],
                'total_industries': 0
            },
            'volume_price_features': {
                'turnover_rate': {'avg': 0, 'max': 0, 'min': 0},
                'volume_ratio': {'avg': 0, 'max': 0, 'min': 0}
            },
            'time_distribution': {
                'note': '首板时间分析需要历史K线数据，当前版本暂不支持',
                'suggestion': '建议后续版本增加首板时间追踪功能'
            },
            'score_distribution': {
                'note': '无评分数据'
            },
            'patterns': [],
            'recommendations': []
        }
        
        if not missed_cases:
            logger.warning("没有找到踏空案例，无法进行模式分析")
            default_result['recommendations'].append("✅ 暂无踏空案例，系统表现良好")
            return default_result
        
        logger.info(f"共找到 {len(missed_cases)} 个踏空案例")
        
        # 2. 获取每只股票的详细信息（市值、行业、量价）
        enriched_cases = self._enrich_cases_with_details(missed_cases)
        
        if not enriched_cases:
            logger.warning("无法获取股票详细信息，模式分析失败")
            default_result['total_cases'] = len(missed_cases)
            default_result['recommendations'].append("⚠️ 无法获取股票详细信息，请检查网络连接")
            return default_result
        
        # 3. 进行聚类分析
        analysis_result = {
            'total_cases': len(enriched_cases),
            'date_range': {
                'start': min(c['date'] for c in enriched_cases),
                'end': max(c['date'] for c in enriched_cases)
            },
            'market_cap_distribution': self._analyze_market_cap(enriched_cases),
            'industry_distribution': self._analyze_industry(enriched_cases),
            'volume_price_features': self._analyze_volume_price(enriched_cases),
            'time_distribution': self._analyze_time_distribution(enriched_cases),
            'score_distribution': self._analyze_score_distribution(enriched_cases)
        }
        
        # 4. 生成模式发现和优化建议
        patterns, recommendations = self._generate_insights(analysis_result)
        
        analysis_result['patterns'] = patterns
        analysis_result['recommendations'] = recommendations
        
        # 5. 保存分析结果
        self._save_pattern_analysis(analysis_result)
        
        return analysis_result
    
    def _load_missed_cases(self, days: int) -> List[Dict]:
        """
        加载过去N天的踏空案例
        
        Args:
            days: 天数
        
        Returns:
            案例列表
        """
        cases = []
        end_date = datetime.now()
        
        for i in range(days):
            date = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
            filepath = self.missed_dir / f"missed_{date}.csv"
            
            if filepath.exists():
                try:
                    df = pd.read_csv(filepath, encoding='utf-8-sig')
                    
                    # 确保股票代码保持字符串格式
                    if 'stock_code' in df.columns:
                        df['stock_code'] = df['stock_code'].astype(str)
                    
                    case_list = df.to_dict('records')
                    cases.extend(case_list)
                    logger.info(f"加载 {date} 的踏空案例: {len(case_list)} 个")
                except Exception as e:
                    logger.error(f"加载 {filepath} 失败: {e}")
        
        return cases
    
    def _enrich_cases_with_details(self, cases: List[Dict]) -> List[Dict]:
        """
        为案例添加详细信息（市值、行业、量价）
        
        Args:
            cases: 原始案例列表
        
        Returns:
            增强后的案例列表
        """
        enriched = []
        
        for case in cases:
            stock_code = case['stock_code']
            
            try:
                # 获取股票详细信息
                stock_details = self._get_stock_details(stock_code)
                
                if stock_details:
                    enriched_case = {**case, **stock_details}
                    enriched.append(enriched_case)
                else:
                    logger.warning(f"无法获取 {stock_code} 的详细信息")
                    
            except Exception as e:
                logger.error(f"获取 {stock_code} 详细信息失败: {e}")
        
        return enriched
    
    def _get_stock_details(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票详细信息（市值、行业、量价）
        
        Args:
            stock_code: 股票代码
        
        Returns:
            股票详细信息字典
        """
        try:
            import akshare as ak
            
            # 获取个股信息
            stock_info = ak.stock_individual_info_em(symbol=stock_code)
            
            if stock_info is None or stock_info.empty:
                return None
            
            # 转换为字典
            info_dict = stock_info.set_index('item')['value'].to_dict()
            
            # 提取关键信息
            details = {
                'market_cap': self._parse_market_cap(info_dict.get('总市值', '0')),
                'circulating_cap': self._parse_market_cap(info_dict.get('流通市值', '0')),
                'industry': info_dict.get('所属行业', '未知'),
                'concept': info_dict.get('概念', ''),
                'pe_ratio': self._parse_float(info_dict.get('市盈率-动态', '0')),
                'pb_ratio': self._parse_float(info_dict.get('市净率', '0'))
            }
            
            # 获取实时行情数据（量价信息）
            realtime_data = self.dm.get_realtime_data(stock_code)
            
            if realtime_data:
                details.update({
                    'turnover_rate': realtime_data.get('turnover_rate', 0),
                    'volume_ratio': realtime_data.get('volume_ratio', 0),
                    'current_price': realtime_data.get('current', 0),
                    'change_percent': realtime_data.get('change_percent', 0)
                })
            
            return details
            
        except ImportError:
            logger.error("akshare模块未安装")
            return None
        except Exception as e:
            logger.error(f"获取 {stock_code} 详细信息失败: {e}")
            return None
    
    def _parse_market_cap(self, value_str: str) -> float:
        """
        解析市值字符串
        
        Args:
            value_str: 市值字符串，如 "123.45亿"
        
        Returns:
            市值（亿元）
        """
        try:
            if isinstance(value_str, str):
                # 移除所有非数字字符（保留小数点）
                import re
                num_str = re.sub(r'[^\d.]', '', value_str)
                return float(num_str) if num_str else 0.0
            elif isinstance(value_str, (int, float)):
                return float(value_str)
            else:
                return 0.0
        except:
            return 0.0
    
    def _parse_float(self, value_str: str) -> float:
        """
        解析浮点数字符串
        
        Args:
            value_str: 浮点数字符串
        
        Returns:
            浮点数
        """
        try:
            if isinstance(value_str, str):
                return float(value_str)
            elif isinstance(value_str, (int, float)):
                return float(value_str)
            else:
                return 0.0
        except:
            return 0.0
    
    def _analyze_market_cap(self, cases: List[Dict]) -> Dict:
        """
        分析市值分布
        
        Args:
            cases: 案例列表
        
        Returns:
            市值分布统计
        """
        micro_cap = []  # < 20亿
        small_mid_cap = []  # 20-100亿
        large_cap = []  # > 100亿
        
        for case in cases:
            cap = case.get('market_cap', 0)
            
            if cap < 20:
                micro_cap.append(cap)
            elif cap < 100:
                small_mid_cap.append(cap)
            else:
                large_cap.append(cap)
        
        total = len(cases)
        
        return {
            'micro_cap': {
                'count': len(micro_cap),
                'percentage': len(micro_cap) / total * 100 if total > 0 else 0,
                'avg_cap': sum(micro_cap) / len(micro_cap) if micro_cap else 0
            },
            'small_mid_cap': {
                'count': len(small_mid_cap),
                'percentage': len(small_mid_cap) / total * 100 if total > 0 else 0,
                'avg_cap': sum(small_mid_cap) / len(small_mid_cap) if small_mid_cap else 0
            },
            'large_cap': {
                'count': len(large_cap),
                'percentage': len(large_cap) / total * 100 if total > 0 else 0,
                'avg_cap': sum(large_cap) / len(large_cap) if large_cap else 0
            }
        }
    
    def _analyze_industry(self, cases: List[Dict]) -> Dict:
        """
        分析行业分布
        
        Args:
            cases: 案例列表
        
        Returns:
            行业分布统计
        """
        industries = [case.get('industry', '未知') for case in cases]
        industry_counter = Counter(industries)
        
        # 获取Top 3行业
        top_3 = industry_counter.most_common(3)
        
        total = len(cases)
        
        return {
            'top_3': [
                {
                    'industry': ind,
                    'count': count,
                    'percentage': count / total * 100
                }
                for ind, count in top_3
            ],
            'total_industries': len(industry_counter)
        }
    
    def _analyze_volume_price(self, cases: List[Dict]) -> Dict:
        """
        分析量价特征
        
        Args:
            cases: 案例列表
        
        Returns:
            量价特征统计
        """
        turnover_rates = [case.get('turnover_rate', 0) for case in cases if case.get('turnover_rate')]
        volume_ratios = [case.get('volume_ratio', 0) for case in cases if case.get('volume_ratio')]
        
        return {
            'turnover_rate': {
                'avg': sum(turnover_rates) / len(turnover_rates) if turnover_rates else 0,
                'max': max(turnover_rates) if turnover_rates else 0,
                'min': min(turnover_rates) if turnover_rates else 0
            },
            'volume_ratio': {
                'avg': sum(volume_ratios) / len(volume_ratios) if volume_ratios else 0,
                'max': max(volume_ratios) if volume_ratios else 0,
                'min': min(volume_ratios) if volume_ratios else 0
            }
        }
    
    def _analyze_time_distribution(self, cases: List[Dict]) -> Dict:
        """
        分析时间分布（首板时间）
        
        注意：当前数据中没有首板时间信息，返回占位符
        未来可以从历史K线数据中提取首板时间
        
        Args:
            cases: 案例列表
        
        Returns:
            时间分布统计
        """
        # TODO: 从历史K线数据中提取首板时间
        return {
            'note': '首板时间分析需要历史K线数据，当前版本暂不支持',
            'suggestion': '建议后续版本增加首板时间追踪功能'
        }
    
    def _analyze_score_distribution(self, cases: List[Dict]) -> Dict:
        """
        分析系统评分分布
        
        Args:
            cases: 案例列表
        
        Returns:
            评分分布统计
        """
        scores = [case.get('system_score', 0) for case in cases if case.get('system_score') is not None]
        
        if not scores:
            return {'note': '无评分数据'}
        
        return {
            'avg': sum(scores) / len(scores),
            'max': max(scores),
            'min': min(scores),
            'distribution': {
                'very_low': len([s for s in scores if s < 40]),
                'low': len([s for s in scores if 40 <= s < 50]),
                'medium': len([s for s in scores if 50 <= s < 60]),
                'high': len([s for s in scores if s >= 60])
            }
        }
    
    def _generate_insights(self, analysis: Dict) -> Tuple[List[Dict], List[str]]:
        """
        生成模式发现和优化建议
        
        Args:
            analysis: 分析结果
        
        Returns:
            (模式发现列表, 优化建议列表)
        """
        patterns = []
        recommendations = []
        
        total = analysis['total_cases']
        threshold_ratio = 0.6  # 60%阈值
        
        # 1. 市值模式分析
        market_cap = analysis['market_cap_distribution']
        if market_cap['micro_cap']['percentage'] > threshold_ratio * 100:
            patterns.append({
                'type': '市值',
                'pattern': '微盘股偏好',
                'description': f"踏空案例中 {market_cap['micro_cap']['percentage']:.1f}% 为微盘股（<20亿）"
            })
            recommendations.append(
                f"⚠️ 发现新模式：微盘股踏空率高 ({market_cap['micro_cap']['percentage']:.1f}%)。"
                f"建议降低小市值股票的资金流出惩罚阈值。"
            )
        
        if market_cap['large_cap']['percentage'] > threshold_ratio * 100:
            patterns.append({
                'type': '市值',
                'pattern': '大盘股偏好',
                'description': f"踏空案例中 {market_cap['large_cap']['percentage']:.1f}% 为大盘股（>100亿）"
            })
            recommendations.append(
                f"⚠️ 发现新模式：大盘股踏空率高 ({market_cap['large_cap']['percentage']:.1f}%)。"
                f"建议增加大盘股的趋势权重。"
            )
        
        # 2. 行业模式分析
        industry = analysis['industry_distribution']
        if industry['top_3']:
            top_industry = industry['top_3'][0]
            if top_industry['percentage'] > threshold_ratio * 100:
                patterns.append({
                    'type': '行业',
                    'pattern': f'{top_industry["industry"]}板块集中',
                    'description': f"踏空案例中 {top_industry['percentage']:.1f}% 属于 {top_industry['industry']} 板块"
                })
                recommendations.append(
                    f"⚠️ 发现新模式：{top_industry['industry']}板块踏空率高 ({top_industry['percentage']:.1f}%)。"
                    f"建议调高该板块的热度权重。"
                )
        
        # 3. 量价特征分析
        volume_price = analysis['volume_price_features']
        if volume_price['turnover_rate']['avg'] > 10:
            patterns.append({
                'type': '量价',
                'pattern': '高换手率',
                'description': f"踏空案例平均换手率为 {volume_price['turnover_rate']['avg']:.2f}%"
            })
            recommendations.append(
                f"⚠️ 发现新模式：踏空股票平均换手率较高 ({volume_price['turnover_rate']['avg']:.2f}%)。"
                f"建议增加换手率因子的权重。"
            )
        
        # 4. 评分分布分析
        score_dist = analysis['score_distribution']
        if 'avg' in score_dist:
            if score_dist['avg'] < 45:
                patterns.append({
                    'type': '评分',
                    'pattern': '低评分踏空',
                    'description': f"踏空案例平均系统评分为 {score_dist['avg']:.1f}"
                })
                recommendations.append(
                    f"⚠️ 发现新模式：踏空股票平均评分较低 ({score_dist['avg']:.1f})。"
                    f"建议检查评分算法是否过于保守。"
                )
        
        # 如果没有发现明显模式
        if not patterns:
            patterns.append({
                'type': '通用',
                'pattern': '无明显模式',
                'description': f"过去 {analysis['total_cases']} 个踏空案例分布较为均匀"
            })
            recommendations.append("✅ 未发现明显模式，当前策略较为均衡。")
        
        return patterns, recommendations
    
    def _save_pattern_analysis(self, analysis: Dict):
        """
        保存模式分析结果
        
        Args:
            analysis: 分析结果
        """
        try:
            # 保存为JSON
            import json
            analysis_file = self.base_dir / "pattern_analysis.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)
            
            logger.info(f"模式分析结果已保存到 {analysis_file}")
            
            # 生成Markdown报告
            self._generate_pattern_report(analysis)
            
        except Exception as e:
            logger.error(f"保存模式分析结果失败: {e}")
    
    def _generate_pattern_report(self, analysis: Dict):
        """
        生成模式分析Markdown报告
        
        Args:
            analysis: 分析结果
        """
        report = f"""
# V14.3 模式捕获分析报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 分析摘要

- **分析周期**: {analysis['date_range']['start']} 至 {analysis['date_range']['end']}
- **踏空案例总数**: {analysis['total_cases']} 个

---

## 🎯 模式发现

"""
        
        for pattern in analysis['patterns']:
            report += f"""
### {pattern['type']} - {pattern['pattern']}
{pattern['description']}

"""
        
        report += """
---

## 💡 优化建议

"""
        
        for rec in analysis['recommendations']:
            report += f"{rec}\n\n"
        
        report += """
---

## 📈 详细数据

### 市值分布
- **微盘股 (<20亿)**: {micro_count} 个 ({micro_pct:.1f}%)
- **中小盘股 (20-100亿)**: {small_count} 个 ({small_pct:.1f}%)
- **大盘股 (>100亿)**: {large_count} 个 ({large_pct:.1f}%)

### 行业分布 (Top 3)
""".format(
            micro_count=analysis['market_cap_distribution']['micro_cap']['count'],
            micro_pct=analysis['market_cap_distribution']['micro_cap']['percentage'],
            small_count=analysis['market_cap_distribution']['small_mid_cap']['count'],
            small_pct=analysis['market_cap_distribution']['small_mid_cap']['percentage'],
            large_count=analysis['market_cap_distribution']['large_cap']['count'],
            large_pct=analysis['market_cap_distribution']['large_cap']['percentage']
        )
        
        for ind in analysis['industry_distribution']['top_3']:
            report += f"- **{ind['industry']}**: {ind['count']} 个 ({ind['percentage']:.1f}%)\n"
        
        report += f"""
### 量价特征
- **平均换手率**: {analysis['volume_price_features']['turnover_rate']['avg']:.2f}%
- **平均量比**: {analysis['volume_price_features']['volume_ratio']['avg']:.2f}

### 评分分布
"""
        
        if 'avg' in analysis['score_distribution']:
            score_dist = analysis['score_distribution']
            report += f"""
- **平均评分**: {score_dist['avg']:.1f}
- **最高评分**: {score_dist['max']:.1f}
- **最低评分**: {score_dist['min']:.1f}
"""
        
        report += f"""

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*V14.3 Pattern Hunter v1.0*
"""
        
        # 保存报告
        report_file = self.base_dir / "pattern_analysis_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"模式分析报告已保存到 {report_file}")


def run_daily_review(date: str = None):
    """
    运行每日复盘
    
    Args:
        date: 日期字符串，格式YYYY-MM-DD，默认为今天
    """
    logger.info("="*60)
    logger.info("V14 AutoReviewer 每日复盘开始")
    logger.info("="*60)
    
    try:
        reviewer = AutoReviewer()
        report = reviewer.generate_daily_report(date)
        
        print(report)
        logger.info("每日复盘完成")
        
    except Exception as e:
        logger.error(f"每日复盘失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # 运行每日复盘
    run_daily_review()
