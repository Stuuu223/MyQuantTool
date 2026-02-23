"""
CTO-A6: 12月31日单日炼蛊回演 - 最终审判第一步
验证V18核心的动态乘数权重公式和横向吸血PK算法

执行流程:
1. 读取data/cleaned_candidates_66.csv（66只票）
2. 使用xtquant读取每只票2025-12-31的Tick数据
3. 计算5分钟窗口（手→股转换）
4. 调用V18核心的calculate_blood_sucking_score计算得分
5. 使用rank_by_capital_share进行横向吸血PK排序
6. 生成最终Top 10排名
"""

import sys
sys.path.insert(0, r'E:\MyQuantTool')

from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import List, Dict, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入xtquant（在venv_qmt环境中）
try:
    from xtquant import xtdata
    logger.info("✅ xtquant导入成功")
except ImportError as e:
    logger.error(f"❌ xtquant导入失败: {e}")
    logger.error("请在venv_qmt环境中运行此脚本")
    raise

# 导入V18核心
from logic.strategies.production.unified_warfare_core import UnifiedWarfareCoreV18


class Day1FinalBattle:
    """
    12月31日单日炼蛊回演器
    """
    
    def __init__(self, date: str = '20251231'):
        """
        初始化回演器
        
        Args:
            date: 交易日期，格式YYYYMMDD
        """
        self.date = date
        self.date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        self.stock_list: List[str] = []
        self.stock_info: Dict[str, Dict] = {}
        
        # 初始化V18核心
        self.v18_core = UnifiedWarfareCoreV18()
        
        # 存储结果
        self.all_stocks_data: Dict[str, List[Dict]] = {}
        self.analysis_results: List[Dict] = []
        self.ranked_results: List[Dict] = []
        
        logger.info(f"=" * 70)
        logger.info(f"【Day1FinalBattle】12月31日单日炼蛊回演初始化")
        logger.info(f"=" * 70)
        logger.info(f"目标日期: {self.date_fmt}")
        
    def load_stock_list(self) -> List[str]:
        """
        从CSV加载66只票列表
        
        Returns:
            股票代码列表
        """
        csv_path = Path(r'E:\MyQuantTool\data\cleaned_candidates_66.csv')
        
        if not csv_path.exists():
            raise FileNotFoundError(f"找不到文件: {csv_path}")
        
        df = pd.read_csv(csv_path)
        
        # 提取股票代码和基本信息
        for _, row in df.iterrows():
            ts_code = row['ts_code']
            self.stock_list.append(ts_code)
            self.stock_info[ts_code] = {
                'name': row['name'],
                'industry': row['industry'],
                'avg_amount_5d': row['avg_amount_5d'],
                'turnover_rate_5d': row['turnover_rate'],
                'volume_ratio': row['volume_ratio']
            }
        
        logger.info(f"✅ 加载完成: 共 {len(self.stock_list)} 只票")
        return self.stock_list
    
    def download_tick_data(self, stock_code: str) -> Optional[pd.DataFrame]:
        """
        使用xtquant下载指定日期的Tick数据
        
        Args:
            stock_code: 股票代码 (如 '300986.SZ')
            
        Returns:
            Tick数据DataFrame，失败返回None
        """
        try:
            # QMT时间格式: YYYYMMDDHHMMSS
            start_time = f"{self.date}093000"
            end_time = f"{self.date}150000"
            
            # 下载Tick数据
            xtdata.download_history_data(
                stock_code=stock_code,
                period='tick',
                start_time=start_time,
                end_time=end_time
            )
            
            # 获取本地数据
            tick_data = xtdata.get_local_data(
                stock_list=[stock_code],
                period='tick',
                start_time=start_time,
                end_time=end_time
            )
            
            if stock_code not in tick_data or tick_data[stock_code].empty:
                logger.warning(f"⚠️ {stock_code} 无Tick数据")
                return None
            
            df = tick_data[stock_code].copy()
            
            # QMT Tick数据列名映射: lastPrice -> price
            # 确保必要的列存在
            if 'lastPrice' not in df.columns:
                logger.warning(f"⚠️ {stock_code} 缺少lastPrice列，可用列: {list(df.columns)}")
                return None
            
            # 统一列名：将lastPrice映射为price
            df = df.rename(columns={'lastPrice': 'price'})
            
            # 转换时间列 (time列是毫秒时间戳，UTC时间)
            if df['time'].dtype in ['int64', 'int32', 'float64']:
                # 毫秒时间戳转datetime (UTC)，然后转换为北京时间(UTC+8)
                df['datetime'] = pd.to_datetime(df['time'], unit='ms', utc=True).dt.tz_convert('Asia/Shanghai')
            else:
                df['datetime'] = pd.to_datetime(df['time'])
            
            logger.info(f"✅ {stock_code} 下载成功: {len(df)} 条Tick")
            return df
            
        except Exception as e:
            logger.error(f"❌ {stock_code} 下载失败: {e}")
            return None
    
    def calculate_5min_windows(self, stock_code: str, tick_df: pd.DataFrame) -> List[Dict]:
        """
        将Tick数据聚合为5分钟窗口
        
        Args:
            stock_code: 股票代码
            tick_df: Tick数据DataFrame
            
        Returns:
            5分钟窗口列表，每个窗口包含:
            - time: 窗口结束时间
            - volume: 成交量(股) - 已从手转换为股
            - amount: 成交额(元)
            - price: 收盘价
            - change_pct: 涨跌幅(%)
            - intensity_score: 强度得分
        """
        if tick_df is None or tick_df.empty:
            return []
        
        # 设置时间索引
        df = tick_df.copy()
        
        # 确保datetime列存在且是datetime类型
        if 'datetime' not in df.columns:
            logger.warning(f"⚠️ {stock_code} 缺少datetime列")
            return []
        
        df.set_index('datetime', inplace=True)
        df.sort_index(inplace=True)
        
        # 只保留交易时间数据 (09:30-11:30, 13:00-15:00)
        # 使用time索引过滤
        morning = df.between_time('09:30', '11:30')
        afternoon = df.between_time('13:00', '15:00')
        df = pd.concat([morning, afternoon])
        
        if df.empty:
            logger.warning(f"⚠️ {stock_code} 无有效交易时间数据，总数据{len(tick_df)}条")
            # 输出一些调试信息
            logger.debug(f"   时间范围: {tick_df['datetime'].min()} ~ {tick_df['datetime'].max()}")
            return []
        
        windows = []
        
        # 按5分钟重采样
        # volume: 累加 (注意: Tick数据的volume是手，需要×100转为股)
        # amount: 累加
        # price: 最后一个价格
        resampled = df.resample('5min').agg({
            'volume': 'sum',
            'amount': 'sum',
            'price': 'last'
        }).dropna()
        
        # 计算前收盘价（用于计算涨跌幅）
        prev_close = df['price'].iloc[0]  # 近似用第一笔价格
        
        for timestamp, row in resampled.iterrows():
            # 转换volume: 手 → 股 (×100)
            volume_shares = row['volume'] * 100
            amount = row['amount']
            price = row['price']
            
            # 计算涨跌幅
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            # 计算强度得分（用于找到最强窗口）
            # 基于成交额和换手率的综合指标
            intensity_score = amount / 10000  # 万元为单位
            
            window = {
                'time': timestamp.strftime('%H:%M'),
                'volume': volume_shares,  # 股
                'amount': amount,  # 元
                'price': price,
                'change_pct': round(change_pct, 2),
                'intensity_score': round(intensity_score, 2)
            }
            windows.append(window)
            
            # 更新前收盘价
            prev_close = price
        
        logger.info(f"   {stock_code}: {len(windows)} 个5分钟窗口")
        return windows
    
    def calculate_all_scores(self) -> Dict[str, Dict]:
        """
        计算所有股票的得分
        
        首先收集所有股票的5分钟窗口数据，然后计算每只票的抽血占比得分
        
        Returns:
            股票代码到得分的映射
        """
        logger.info(f"\n{'=' * 70}")
        logger.info(f"【步骤1】下载并处理所有股票的Tick数据")
        logger.info(f"{'=' * 70}")
        
        # 1. 下载并处理所有股票的Tick数据
        for stock_code in self.stock_list:
            try:
                tick_df = self.download_tick_data(stock_code)
                if tick_df is not None:
                    windows = self.calculate_5min_windows(stock_code, tick_df)
                    if windows:
                        self.all_stocks_data[stock_code] = windows
            except Exception as e:
                logger.error(f"❌ {stock_code} 处理失败: {e}")
                continue
        
        if not self.all_stocks_data:
            logger.error("❌ 无有效数据")
            return {}
        
        logger.info(f"\n✅ 数据处理完成: {len(self.all_stocks_data)}/{len(self.stock_list)} 只票有数据")
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"【步骤2】使用V18核心计算抽血占比动态乘数得分")
        logger.info(f"{'=' * 70}")
        
        # 2. 计算每只票的得分
        scores = {}
        for stock_code, windows in self.all_stocks_data.items():
            try:
                # 使用V18核心计算抽血占比得分
                score_result = self.v18_core.calculate_blood_sucking_score(
                    stock_code=stock_code,
                    windows=windows,
                    all_stocks_data=self.all_stocks_data
                )
                
                # 执行全天分析（获取换手率、成交额等）
                day_analysis = self.v18_core.analyze_day(stock_code, self.date, windows)
                
                if 'error' in day_analysis:
                    logger.warning(f"⚠️ {stock_code} 分析失败: {day_analysis['error']}")
                    continue
                
                # 组合结果
                result = {
                    'stock_code': stock_code,
                    'name': self.stock_info.get(stock_code, {}).get('name', 'Unknown'),
                    'industry': self.stock_info.get(stock_code, {}).get('industry', 'Unknown'),
                    'base_score': score_result['base_score'],
                    'capital_share_pct': score_result['capital_share_pct'],
                    'multiplier': score_result['multiplier'],
                    'final_score': score_result['final_score'],
                    'total_amount': day_analysis.get('total_amount', 0),
                    'turnover_rate': day_analysis.get('turnover_rate', 0),
                    'is_strong_momentum': day_analysis.get('is_strong_momentum', False),
                    'window_count': len(windows)
                }
                
                scores[stock_code] = result
                self.analysis_results.append(result)
                
            except Exception as e:
                logger.error(f"❌ {stock_code} 得分计算失败: {e}")
                continue
        
        logger.info(f"✅ 得分计算完成: {len(scores)} 只票")
        return scores
    
    def run_blood_sucking_battle(self) -> List[Dict]:
        """
        执行横向吸血PK排序
        
        Returns:
            排序后的结果列表（包含rank字段）
        """
        logger.info(f"\n{'=' * 70}")
        logger.info(f"【步骤3】横向吸血PK排序")
        logger.info(f"{'=' * 70}")
        
        if not self.analysis_results:
            logger.error("❌ 无分析结果，无法排序")
            return []
        
        # 使用V18核心的rank_by_capital_share进行排序
        self.ranked_results = self.v18_core.rank_by_capital_share(self.analysis_results)
        
        # 输出Top 10
        logger.info(f"\n🏆 Top 10 排名:")
        for i, r in enumerate(self.ranked_results[:10], 1):
            logger.info(
                f"   TOP{i}: {r['stock_code']}({r['name']}) "
                f"得分={r['final_score']:.2f} "
                f"(基础{r['base_score']:.1f}×乘数{r['multiplier']:.2f}) "
                f"抽血占比{r['capital_share_pct']:.2f}%"
            )
        
        return self.ranked_results
    
    def generate_report(self) -> Dict:
        """
        生成最终报告
        
        Returns:
            报告字典
        """
        logger.info(f"\n{'=' * 70}")
        logger.info(f"【步骤4】生成最终报告")
        logger.info(f"{'=' * 70}")
        
        # Top 10详细信息
        top10 = self.ranked_results[:10] if len(self.ranked_results) >= 10 else self.ranked_results
        
        # 查找志特新材
        zhitexincai_rank = None
        zhitexincai_in_top10 = False
        zhitexincai_score = 0
        
        for r in self.ranked_results:
            if r['stock_code'] == '300986.SZ':
                zhitexincai_rank = r['rank']
                zhitexincai_in_top10 = r['rank'] <= 10
                zhitexincai_score = r['final_score']
                break
        
        # 计算汇总统计
        total_inflow = sum(r['total_amount'] for r in self.analysis_results)
        all_scores = [r['final_score'] for r in self.analysis_results]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        max_score = max(all_scores) if all_scores else 0
        
        # 构建报告
        report = {
            'trade_date': self.date,
            'total_stocks': len(self.stock_list),
            'valid_stocks': len(self.analysis_results),
            'top10': [
                {
                    'rank': r['rank'],
                    'stock_code': r['stock_code'],
                    'name': r['name'],
                    'industry': r['industry'],
                    'base_score': r['base_score'],
                    'capital_share_pct': r['capital_share_pct'],
                    'multiplier': r['multiplier'],
                    'final_score': r['final_score'],
                    'total_amount': round(r['total_amount'], 2),
                    'turnover_rate': round(r['turnover_rate'], 2),
                    'is_strong_momentum': r['is_strong_momentum']
                }
                for r in top10
            ],
            'zhitexincai': {
                'rank': zhitexincai_rank,
                'in_top10': zhitexincai_in_top10,
                'final_score': zhitexincai_score
            },
            'summary': {
                'total_inflow': round(total_inflow, 2),
                'avg_score': round(avg_score, 2),
                'max_score': round(max_score, 2),
                'validation_passed': zhitexincai_in_top10  # CTO验收红线：志特新材必须在Top10内
            },
            'methodology': {
                'base_score_formula': '资金强度(40) + 换手率(30) + 价格动能(30)',
                'multiplier_formula': '1 + (抽血占比% / 100) * 2',
                'final_score_formula': 'base_score * multiplier',
                'volume_conversion': '手 × 100 = 股',
                'window_size': '5分钟'
            }
        }
        
        # 验收红线检查
        logger.info(f"\n{'=' * 70}")
        logger.info(f"【CTO验收红线检查】")
        logger.info(f"{'=' * 70}")
        logger.info(f"✅ 志特新材排名: {zhitexincai_rank}")
        logger.info(f"✅ 志特新材是否在Top 10: {'通过 ✓' if zhitexincai_in_top10 else '失败 ✗'}")
        logger.info(f"✅ 动态乘数公式: 已应用")
        logger.info(f"✅ 横向吸血PK: 已执行")
        logger.info(f"✅ 参与排名票数: {len(self.analysis_results)}/66")
        
        if zhitexincai_in_top10:
            logger.info(f"\n🎉 验收通过！志特新材在Top 10内")
        else:
            logger.warning(f"\n⚠️ 验收失败！志特新材不在Top 10内")
        
        # 保存报告
        output_path = Path(r'E:\MyQuantTool\data\day1_final_battle_report_20251231.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📄 报告已保存: {output_path}")
        
        return report
    
    def run(self) -> Dict:
        """
        执行完整的回演流程
        
        Returns:
            最终报告
        """
        logger.info(f"\n{'=' * 70}")
        logger.info(f"🚀 开始执行12月31日单日炼蛊回演")
        logger.info(f"{'=' * 70}")
        
        # 1. 加载股票列表
        self.load_stock_list()
        
        # 2. 计算所有得分
        self.calculate_all_scores()
        
        # 3. 横向吸血PK排序
        self.run_blood_sucking_battle()
        
        # 4. 生成报告
        report = self.generate_report()
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"✅ 回演完成！")
        logger.info(f"{'=' * 70}")
        
        return report


def main():
    """
    主函数
    """
    # 创建回演器并执行
    battle = Day1FinalBattle(date='20251231')
    report = battle.run()
    
    # 输出关键结果
    print("\n" + "=" * 70)
    print("【12月31日单日炼蛊回演 - 最终结果】")
    print("=" * 70)
    print(f"\n交易日期: {report['trade_date']}")
    print(f"总票数: {report['total_stocks']}")
    print(f"有效票数: {report['valid_stocks']}")
    print(f"\n志特新材排名: {report['zhitexincai']['rank']}")
    print(f"志特新材是否在Top 10: {'✅ 是' if report['zhitexincai']['in_top10'] else '❌ 否'}")
    print(f"\n汇总统计:")
    print(f"  - 全池总净流入: {report['summary']['total_inflow']/10000:.1f}万元")
    print(f"  - 平均得分: {report['summary']['avg_score']:.2f}")
    print(f"  - 最高得分: {report['summary']['max_score']:.2f}")
    print(f"\n🏆 Top 10 排名:")
    for item in report['top10']:
        print(f"  TOP{item['rank']}: {item['stock_code']}({item['name']}) - "
              f"得分{item['final_score']:.2f}(基础{item['base_score']:.1f}×乘数{item['multiplier']:.2f})")
    
    print("\n" + "=" * 70)
    if report['summary']['validation_passed']:
        print("🎉 CTO验收通过！志特新材在Top 10内")
    else:
        print("⚠️ CTO验收失败！志特新材不在Top 10内")
    print("=" * 70)
    
    return report


if __name__ == '__main__':
    main()
