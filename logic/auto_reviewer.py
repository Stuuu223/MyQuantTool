"""
V14 AutoReviewer - 自动化案例收集与复盘系统

功能：
1. "打脸"案例集：系统评分>85但次日跌幅>3%
2. "踏空"案例集：系统评分<60但今日涨停
3. "救命"案例集：被事实熔断按住但次日大跌

使用：
每天15:30收盘后运行，生成《每日异常交易报告》
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from pathlib import Path
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
