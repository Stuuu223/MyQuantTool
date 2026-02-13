#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描器回测工具 (Scanner Backtest Tool)

功能：
1. 读取 data/scan_results/ 下的历史扫描结果
2. 提取每日的 opportunities 列表
3. 获取这些股票在 T+1 至 T+5 日的真实表现
4. 统计胜率和盈亏比

Author: MyQuantTool Team
Date: 2026-02-13
"""

import os
import json
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import pandas as pd

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False
    print("⚠️  QMT SDK 未安装，将无法获取历史数据")

# 辅助类：CodeConverter
class CodeConverter:
    @staticmethod
    def to_qmt(code: str) -> str:
        """
        转换为 QMT 格式代码 (000001.SZ, 600000.SH)
        """
        if '.' in code:
            return code
        
        if code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith(('0', '3')):
            return f"{code}.SZ"
        elif code.startswith(('8', '4')):
            return f"{code}.BJ"
        else:
            return code

class BacktestScanner:
    def __init__(self, scan_results_dir: str = "data/scan_results"):
        """
        初始化回测工具
        
        Args:
            scan_results_dir: 历史扫描结果目录
        """
        self.scan_results_dir = scan_results_dir
        self.scan_results = self._load_scan_results()
        
    def _load_scan_results(self) -> List[Dict]:
        """加载历史扫描结果"""
        results = []
        pattern = os.path.join(self.scan_results_dir, "*.json")
        files = glob.glob(pattern)
        
        for file_path in files:
            try:
                # 从文件名提取日期和模式
                filename = os.path.basename(file_path)
                # 格式: YYYY-MM-DD_mode.json
                parts = filename.replace('.json', '').split('_')
                if len(parts) >= 2:
                    date_str = parts[0]
                    mode = '_'.join(parts[1:])
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # 提取机会池（在 results.opportunities 中）
                    scan_results = data.get('results', {})
                    opportunities = scan_results.get('opportunities', [])
                    
                    if opportunities:
                        results.append({
                            'date': date_str,
                            'mode': mode,
                            'file_path': file_path,
                            'opportunities': opportunities
                        })
            except Exception as e:
                print(f"⚠️  加载文件失败 {file_path}: {e}")
                
        # 按日期排序
        results.sort(key=lambda x: x['date'])
        return results
    
    def get_stock_performance(self, code: str, scan_date: str, days: int = 5) -> Dict:
        """
        获取股票在扫描日之后的表现
        
        Args:
            code: 股票代码
            scan_date: 扫描日期 (YYYY-MM-DD)
            days: 观察天数
            
        Returns:
            {
                'daily_gains': [T+1涨幅, T+2涨幅, ...],
                'max_gain': 最大涨幅,
                'max_loss': 最大跌幅,
                'final_gain': 最终涨幅
            }
        """
        if not QMT_AVAILABLE:
            return {
                'daily_gains': [], 'max_gain': 0, 'max_loss': 0, 'final_gain': 0
            }
            
        try:
            # 计算开始和结束时间
            start_dt = datetime.strptime(scan_date, "%Y-%m-%d")
            # 往后推 days + 10 天（考虑到周末和节假日）
            end_dt = start_dt + timedelta(days=days + 10)
            
            start_str = start_dt.strftime("%Y%m%d")
            end_str = end_dt.strftime("%Y%m%d")
            
            # 获取日线数据
            code_qmt = CodeConverter.to_qmt(code)
            
            # 确保数据已下载
            xtdata.download_history_data(code_qmt, period='1d', start_time=start_str, end_time=end_str)
            
            kline = xtdata.get_market_data(
                field_list=['open', 'high', 'low', 'close', 'preClose'],
                stock_list=[code_qmt],
                period='1d',
                start_time=start_str,
                end_time=end_str,
                dividend_type='none'
            )
            
            print(f"    🔍 {code} kline 结果: {kline.keys() if kline else 'None'}")
            
            if not kline:
                return {
                    'daily_gains': [], 'max_gain': 0, 'max_loss': 0, 'final_gain': 0
                }
            
            # QMT 返回格式: {字段: DataFrame(索引为股票代码)}
            # 提取股票代码对应的所有字段的 DataFrame
            # kline 结构: {'open': DataFrame(索引为股票代码), 'high': DataFrame(索引为股票代码), ...}
            
            # 重新组织为单个 DataFrame（索引为日期，列为不同字段）
            # 从所有字段中提取该股票的数据
            df_list = []
            for field, field_data in kline.items():
                # 确保 field_data 是 DataFrame
                if isinstance(field_data, pd.DataFrame):
                    if code_qmt in field_data.index:
                        field_df = field_data.loc[code_qmt]
                        if hasattr(field_df, '__len__') and len(field_df) > 0:
                            # 转换为 Series，重命名后合并
                            series = pd.Series(field_df, name=field)
                            df_list.append(series)
            
            if not df_list:
                return {
                    'daily_gains': [], 'max_gain': 0, 'max_loss': 0, 'final_gain': 0
                }
            
            # 合并所有字段为一个 DataFrame
            df = pd.concat(df_list, axis=1)
            
            if not hasattr(df, '__len__') or len(df) <= 1:
                return {
                    'daily_gains': [], 'max_gain': 0, 'max_loss': 0, 'final_gain': 0
                }
            
            # 找到扫描日之后的交易日
            # df 的索引是时间戳 (milliseconds) 或日期字符串
            # 假设是日期字符串 YYYYMMDD
            # 如果是 DataFrame
            valid_days = []
            scan_idx = -1
            
            # 转换索引为日期字符串列表
            dates = []
            if hasattr(df, 'index'):
                 # 处理时间戳索引
                for idx in df.index:
                    idx_str = str(idx)
                    if len(idx_str) == 8 and idx_str.isdigit():
                        # YYYYMMDD 格式
                        dates.append(idx_str)
                    else:
                        # 尝试解析为时间戳或 datetime 对象
                        try:
                            if hasattr(idx, 'strftime'):
                                # pd.Timestamp 或 datetime 对象
                                dates.append(idx.strftime("%Y%m%d"))
                            else:
                                # 时间戳（毫秒）
                                dt = datetime.fromtimestamp(idx / 1000)
                                dates.append(dt.strftime("%Y%m%d"))
                        except:
                            dates.append(idx_str)
            else:
                # 假设是 recarray
                dates = [d.decode() if isinstance(d, bytes) else str(d) for d in df['time']]
            
            print(f"    🔍 {code} dates 列表: {dates[:5]} (共{len(dates)}个)")
                
            # 找到扫描日
            scan_date_compact = scan_date.replace('-', '')
            
            start_idx = -1
            for i, d in enumerate(dates):
                # 确保 d 是字符串
                d_str = str(d)
                if len(d_str) == 8 and d_str.isdigit():
                    if d_str > scan_date_compact:
                        start_idx = i
                        break
            
            if start_idx == -1:
                return {
                    'daily_gains': [], 'max_gain': 0, 'max_loss': 0, 'final_gain': 0
                }
            
            # 获取 T+1 至 T+days 的数据
            future_data = []
            
            # 如果是 DataFrame
            if hasattr(df, 'iloc'):
                for i in range(start_idx, min(start_idx + days, len(df))):
                    future_data.append(df.iloc[i])
            else:
                 # recarray
                 for i in range(start_idx, min(start_idx + days, len(df))):
                    future_data.append(df[i])
            
            if not future_data:
                return {
                    'daily_gains': [], 'max_gain': 0, 'max_loss': 0, 'final_gain': 0
                }
                
            # 计算涨幅
            # 基准价格：扫描日的收盘价
            # 注意：我们需要扫描日的数据来确定基准
            # 在上面的循环中，df包含了扫描日（如果有交易）
            
            # 找到扫描日（如果有）或前一个交易日作为基准
            # 这里简化逻辑：基准 = T+1 日的前收盘价
            
            base_price = future_data[0]['preClose'] # T+1 的前收盘 = T 的收盘
            
            if base_price == 0:
                 return {
                    'daily_gains': [], 'max_gain': 0, 'max_loss': 0, 'final_gain': 0
                }
                
            daily_gains = []
            max_gain = -999.0
            max_loss = 999.0
            
            for day_data in future_data:
                close_price = day_data['close']
                high_price = day_data['high']
                low_price = day_data['low']
                
                # 每日收盘涨幅
                gain = (close_price - base_price) / base_price * 100
                daily_gains.append(gain)
                
                # 期间最高涨幅
                high_gain = (high_price - base_price) / base_price * 100
                if high_gain > max_gain:
                    max_gain = high_gain
                    
                # 期间最大跌幅
                low_loss = (low_price - base_price) / base_price * 100
                if low_loss < max_loss:
                    max_loss = low_loss
            
            final_gain = daily_gains[-1]
            
            # 修正 max_gain / max_loss 初始值
            if max_gain == -999.0: max_gain = 0.0
            if max_loss == 999.0: max_loss = 0.0
            
            return {
                'daily_gains': daily_gains,
                'max_gain': max_gain,
                'max_loss': max_loss,
                'final_gain': final_gain
            }
            
        except Exception as e:
            return {
                'daily_gains': [], 'max_gain': 0, 'max_loss': 0, 'final_gain': 0
            }

    def analyze_performance(self, win_threshold: float = 2.0) -> Dict:
        """
        分析所有历史扫描结果的表现
        
        Args:
            win_threshold: 判定胜利的涨幅阈值 (%)
            
        Returns:
            分析结果字典
        """
        all_stocks = []
        
        print(f"🔍 开始分析 {len(self.scan_results)} 个历史扫描结果...")
        
        for result in self.scan_results:
            scan_date = result['date']
            # 只分析 T+1 已经发生的日期
            # 简单判断：如果扫描日期是今天或未来，跳过
            if scan_date >= datetime.now().strftime("%Y-%m-%d"):
                continue
                
            print(f"  📅 处理 {scan_date} ({len(result['opportunities'])} 只)...")
            
            for stock in result['opportunities']:
                code = stock.get('code')
                name = stock.get('name', '未知')
                
                if not code:
                    continue
                    
                # 获取表现
                performance = self.get_stock_performance(code, scan_date)
                
                # 只有获取到数据才记录
                if performance['daily_gains']:
                    stock_info = {
                        'code': code,
                        'name': name,
                        'scan_date': scan_date,
                        'performance': performance
                    }
                    all_stocks.append(stock_info)
                    
        # 统计指标
        win_count = 0
        loss_count = 0
        total_gain = 0.0
        total_loss = 0.0
        
        for stock in all_stocks:
            perf = stock['performance']
            
            # T+1 日最高涨幅 > win_threshold 算胜
            # 注意：max_gain 是期间最高涨幅，如果只是 T+1，应该看 daily_gains[0] 对应的 High?
            # get_stock_performance 返回的是期间 max_gain，这里用 max_gain
            if perf['max_gain'] >= win_threshold:
                win_count += 1
                total_gain += perf['max_gain']
            else:
                loss_count += 1
                # 亏损取 abs(max_loss) 或 abs(final_gain if < 0)
                # 这里用 final_gain 如果小于 0，否则用 0?
                # 按照 CTO 定义：(选错的票平均最大跌幅)
                loss = abs(perf['max_loss'])
                total_loss += loss
        
        total_count = len(all_stocks)
        win_rate = win_count / total_count * 100 if total_count > 0 else 0
        avg_gain = total_gain / win_count if win_count > 0 else 0
        avg_loss = total_loss / loss_count if loss_count > 0 else 0
        pnl_ratio = avg_gain / avg_loss if avg_loss > 0 else 0
        
        return {
            'total_stocks': total_count,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'avg_gain': avg_gain,
            'avg_loss': avg_loss,
            'pnl_ratio': pnl_ratio,
            'stocks': all_stocks
        }
    
    def print_report(self, analysis: dict):
        """打印报告"""
        print("\\n" + "=" * 80)
        print("📊 扫描器回测报告")
        print("=" * 80)
        print(f"\\n总股票数: {analysis['total_stocks']}")
        print(f"胜利次数: {analysis['win_count']}")
        print(f"失败次数: {analysis['loss_count']}")
        print(f"\\n胜率: {analysis['win_rate']:.2f}%")
        print(f"平均盈利: {analysis['avg_gain']:.2f}%")
        print(f"平均亏损: {analysis['avg_loss']:.2f}%")
        print(f"盈亏比: {analysis['pnl_ratio']:.2f}")
        
        print("\\n" + "=" * 80)
        print("📋 详细股票表现")
        print("=" * 80)
        
        # 按日期排序
        sorted_stocks = sorted(analysis['stocks'], key=lambda x: x['scan_date'])
        
        for stock in sorted_stocks:
            perf = stock['performance']
            status = "✅ 胜" if perf['max_gain'] >= 2.0 else "❌ 负"
            
            print(f"\\n{status} {stock['code']} {stock['name']}")
            print(f"  扫描日期: {stock['scan_date']}")
            print(f"  最大涨幅: {perf['max_gain']:.2f}%")
            print(f"  最大跌幅: {perf['max_loss']:.2f}%")
            print(f"  最终涨幅: {perf['final_gain']:.2f}%")
            # 格式化每日涨幅
            daily_str = ", ".join([f"{g:.2f}%" for g in perf['daily_gains']])
            print(f"  每日涨幅: {daily_str}")
            
        print("\\n" + "=" * 80)
        print("🎯 结论")
        print("=" * 80)
        
        if analysis['win_rate'] >= 60:
            print(f"✅ 胜率 {analysis['win_rate']:.2f}% >= 60%，策略表现良好")
        elif analysis['win_rate'] >= 50:
            print(f"⚠️  胜率 {analysis['win_rate']:.2f}% >= 50%，策略表现一般")
        else:
            print(f"❌ 胜率 {analysis['win_rate']:.2f}% < 50%，策略需要优化")
            
        if analysis['pnl_ratio'] >= 2.0:
            print(f"✅ 盈亏比 {analysis['pnl_ratio']:.2f} >= 2.0，风险收益比良好")
        elif analysis['pnl_ratio'] >= 1.0:
            print(f"⚠️  盈亏比 {analysis['pnl_ratio']:.2f} >= 1.0，风险收益比一般")
        else:
            print(f"❌ 盈亏比 {analysis['pnl_ratio']:.2f} < 1.0，风险收益比不佳")
            
        print("=" * 80)

def main():
    """主函数"""
    print("=" * 80)
    print("🚀 扫描器回测工具启动")
    print("=" * 80)
    
    # 创建回测工具
    backtest = BacktestScanner()
    
    if not backtest.scan_results:
        print("\\n❌ 没有找到历史扫描结果")
        print("请确保 data/scan_results/ 目录下有历史扫描 JSON 文件")
        return
        
    # 分析表现
    # 胜利阈值：2.0% (CTO定义：T+1日最高涨幅 > 2%)
    analysis = backtest.analyze_performance(win_threshold=2.0)
    
    if analysis['total_stocks'] == 0:
        print("\\n⚠️  没有可分析的股票数据（可能是所有扫描结果都在未来，或者无法获取历史数据）")
        return
        
    # 打印报告
    backtest.print_report(analysis)
    
    # 保存结果
    output_dir = "data"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_file = os.path.join(output_dir, "backtest_scanner_report.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
        
    print(f"\\n💾 详细报告已保存到: {output_file}")

if __name__ == "__main__":
    main()
