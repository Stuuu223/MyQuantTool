#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
热门 Top30 生成脚本
数据源：Tushare
频率：日级 EOD，每天收盘后运行
输出：CSV + JSON
"""

import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import tushare as ts
except ImportError:
    print("❌ 未安装tushare，请运行: pip install tushare")
    sys.exit(1)


class HotUniverseBuilder:
    """热门股票池构建器"""
    
    def __init__(self, tushare_token: str = None):
        """
        初始化热门股票池构建器
        
        Args:
            tushare_token: Tushare API Token
        """
        if tushare_token:
            ts.set_token(tushare_token)
        
        self.output_dir = PROJECT_ROOT / 'data' / 'hot_universe'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.output_dir / 'daily_top30').mkdir(exist_ok=True)
        (self.output_dir / 'monthly_pool').mkdir(exist_ok=True)
        (self.output_dir / 'capital_events').mkdir(exist_ok=True)
        
        # 存储月度池数据
        self.monthly_pool = {
            'stocks': {}
        }
    
    def fetch_daily_data(self, trade_date: str) -> pd.DataFrame:
        """
        获取指定日期的市场数据
        
        Args:
            trade_date: 交易日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 市场数据
        """
        try:
            # 获取日线行情
            daily_df = ts.pro_bar(
                ts_code='',
                trade_date=trade_date,
                fields='ts_code,trade_date,open,high,low,close,vol,amount',
                freq='D'
            )
            
            if daily_df.empty:
                print(f"⚠️  {trade_date} 无市场数据")
                return pd.DataFrame()
            
            # 获取基本面数据（流通市值）
            basic_df = ts.pro_bar_basic(
                ts_code='',
                trade_date=trade_date,
                fields='ts_code,trade_date,circ_mv,total_mv',
                freq='D'
            )
            
            if not basic_df.empty:
                daily_df = daily_df.merge(basic_df, on=['ts_code', 'trade_date'], how='left')
            
            return daily_df
            
        except Exception as e:
            print(f"❌ 获取 {trade_date} 数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_hot_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算热门分数
        
        Args:
            df: 市场数据
        
        Returns:
            DataFrame: 带有热门分数的数据
        """
        if df.empty:
            return df
        
        # 过滤条件
        df = df[
            (df['amount'] > 0) &  # 有成交额
            (df['pct_chg'] > -10) &  # 非跌停
            (df['pct_chg'] < 10)     # 非涨停
        ].copy()
        
        # 计算换手率
        df['turnover_rate'] = (df['vol'] * df['close'] / df['amount'] * 100)
        
        # 计算百分位排名
        df['amount_rank_pct'] = df['amount'].rank(pct=True) / len(df)
        df['tvr_rank_pct'] = df['turnover_rate'].rank(pct=True) / len(df)
        
        # 计算综合热度分数
        df['hot_score'] = 0.6 * df['amount_rank_pct'] + 0.4 * df['tvr_rank_pct']
        
        # 涨跌停状态
        df['limit_status'] = 'NONE'
        df.loc[df['pct_chg'] >= 9.9, 'limit_status'] = 'LIMIT_UP'
        df.loc[df['pct_chg'] <= -9.9, 'limit_status'] = 'LIMIT_DOWN'
        
        return df
    
    def get_daily_top30(self, trade_date: str) -> pd.DataFrame:
        """
        获取单日Top30
        
        Args:
            trade_date: 交易日期 (YYYYMMDD)
        
        Returns:
            DataFrame: Top30数据
        """
        df = self.fetch_daily_data(trade_date)
        df = self.calculate_hot_score(df)
        
        if df.empty:
            return pd.DataFrame()
        
        # 按热门分数排序，取Top30
        top30 = df.nlargest(30, 'hot_score')
        
        # 添加股票名称
        try:
            basic_info = ts.pro_bar(
                ts_code='',
                trade_date=trade_date,
                fields='ts_code,name',
                freq='D'
            )
            if not basic_info.empty:
                top30 = top30.merge(basic_info[['ts_code', 'name']], on='ts_code', how='left')
        except:
            pass
        
        # 转换QMT代码
        top30['qmt_code'] = top30['ts_code']
        
        return top30
    
    def save_daily_csv(self, df: pd.DataFrame, trade_date: str):
        """
        保存单日CSV
        
        Args:
            df: Top30数据
            trade_date: 交易日期
        """
        if df.empty:
            return
        
        output_file = self.output_dir / 'daily_top30' / f'hot_top30_{trade_date}.csv'
        
        # 字段顺序
        columns = [
            'ts_code', 'qmt_code', 'name',
            'turnover', 'turnover_rate', 'volume', 'amount',
            'amount_rank_pct', 'tvr_rank_pct', 'hot_score',
            'open', 'high', 'low', 'close', 'pct_chg',
            'limit_status', 'circ_mv', 'total_mv'
        ]
        
        df[columns].to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ 保存CSV: {output_file}")
    
    def update_monthly_pool(self, top30_df: pd.DataFrame, trade_date: str):
        """
        更新月度池
        
        Args:
            top30_df: Top30数据
            trade_date: 交易日期
        """
        if top30_df.empty:
            return
        
        for _, row in top30_df.iterrows():
            code = row['ts_code']
            name = row['name']
            hot_score = row['hot_score']
            
            if code not in self.monthly_pool['stocks']:
                self.monthly_pool['stocks'][code] = {
                    'name': name,
                    'appear_dates': [],
                    'appear_count': 0,
                    'best_rank': 999,
                    'best_score': 0,
                    'last_hot_score': 0
                }
            
            stock_info = self.monthly_pool['stocks'][code]
            stock_info['appear_dates'].append(trade_date)
            stock_info['appear_count'] += 1
            stock_info['last_hot_score'] = hot_score
            
            if hot_score > stock_info['best_score']:
                stock_info['best_score'] = hot_score
    
    def save_monthly_json(self, start_date: str, end_date: str):
        """
        保存月度池JSON
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        """
        # 计算最佳名次
        for code, stock_info in self.monthly_pool['stocks'].items():
            # 假设排名按appear_count倒序
            sorted_stocks = sorted(
                self.monthly_pool['stocks'].items(),
                key=lambda x: x[1]['appear_count'],
                reverse=True
            )
            for idx, (stock_code, _) in enumerate(sorted_stocks, 1):
                if stock_code == code:
                    stock_info['best_rank'] = idx
                    break
        
        # 构建JSON
        output_data = {
            'meta': {
                'window_start': start_date,
                'window_end': end_date,
                'selection_rule_version': 'TOP30_V1',
                'source': 'tushare',
                'generated_at': datetime.now().isoformat()
            },
            'daily_top30': {},  # 可以按日期存储
            'monthly_pool': self.monthly_pool
        }
        
        output_file = self.output_dir / 'monthly_pool' / f'hot_pool_{start_date}_{end_date}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ 保存JSON: {output_file}")
        print(f"   月度池规模: {len(self.monthly_pool['stocks'])} 只股票")


def main():
    """主函数"""
    # Tushare Token配置
    tushare_token = "YOUR_TUSHARE_TOKEN"  # 请替换为真实token
    
    # 参数配置
    end_date = datetime.now()
    start_date = end_date - timedelta(days=20)  # 最近20个交易日
    
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    
    print(f"{'='*60}")
    print(f"🚀 构建热门Top30股票池")
    print(f"{'='*60}")
    print(f"时间窗口: {start_date_str} ~ {end_date_str}")
    print(f"数据源: Tushare")
    print(f"")
    
    # 构建热门池
    builder = HotUniverseBuilder(tushare_token)
    
    # 遍历每个交易日
    trade_dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    for trade_date in trade_dates:
        date_str = trade_date.strftime('%Y%m%d')
        
        print(f"处理 {date_str}...")
        
        # 获取Top30
        top30_df = builder.get_daily_top30(date_str)
        
        if not top30_df.empty:
            # 保存CSV
            builder.save_daily_csv(top30_df, date_str)
            
            # 更新月度池
            builder.update_monthly_pool(top30_df, date_str)
        else:
            print(f"  ⚠️  {date_str} 无数据")
    
    # 保存月度池
    builder.save_monthly_json(start_date_str, end_date_str)
    
    print(f"\n{'='*60}")
    print(f"✅ 热门Top30构建完成")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()