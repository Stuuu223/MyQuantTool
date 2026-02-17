#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
半路突破样本开采器 (Halfway Sample Miner)

功能：
1. 从532只热门股中自动挖掘疑似半路突破的候选片段
2. 生成带价量序列的候选样本文件（JSON格式）
3. 支持人工复核标注

使用流程：
1. 运行开采：python tools/halfway_sample_miner.py --mode mine --days 10
2. 人工复核：查看生成的候选样本，手工标注正/负样本
3. 导入测试：将标注后的样本复制到 tests/real_samples/ 目录

Author: AI Project Director
Version: V1.0
Date: 2026-02-17
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.strategies.unified_warfare_core import get_unified_warfare_core
from logic.data_providers.qmt_historical_provider import QMTHistoricalProvider
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class HalfwaySampleMiner:
    """半路突破样本开采器"""
    
    def __init__(self, output_dir: str = "data/samples/halfway_candidates"):
        """
        初始化开采器
        
        Args:
            output_dir: 候选样本输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取统一战法核心（用于初步筛选）
        self.warfare_core = get_unified_warfare_core()
        
        logger.info(f"✅ [样本开采器] 初始化完成")
        logger.info(f"   - 输出目录: {self.output_dir}")
        logger.info(f"   - 战法核心: {type(self.warfare_core).__name__}")
    
    def mine_candidates(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        min_confidence: float = 0.3
    ) -> List[Dict]:
        """
        开采候选样本
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            min_confidence: 最小置信度阈值
            
        Returns:
            候选样本列表
        """
        candidates = []
        
        # 解析日期范围
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        total_days = (end_dt - start_dt).days + 1
        logger.info(f"🎯 [样本开采] 开始开采")
        logger.info(f"   - 股票数量: {len(stock_codes)}")
        logger.info(f"   - 日期范围: {start_date} 至 {end_date} ({total_days}天)")
        logger.info(f"   - 置信度阈值: {min_confidence}")
        
        # 遍历每只股票、每天
        for stock_code in stock_codes:
            logger.info(f"\n📊 处理股票: {stock_code}")
            
            current_dt = start_dt
            while current_dt <= end_dt:
                date_str = current_dt.strftime("%Y-%m-%d")
                
                try:
                    # 开采单日候选
                    daily_candidates = self._mine_single_day(
                        stock_code, date_str, min_confidence
                    )
                    candidates.extend(daily_candidates)
                    
                    if daily_candidates:
                        logger.info(f"   {date_str}: 发现 {len(daily_candidates)} 个候选")
                    
                except Exception as e:
                    logger.error(f"   {date_str}: 开采失败 - {e}")
                
                current_dt += timedelta(days=1)
        
        logger.info(f"\n✅ [样本开采] 完成")
        logger.info(f"   - 总候选数: {len(candidates)}")
        
        return candidates
    
    def _mine_single_day(
        self,
        stock_code: str,
        date_str: str,
        min_confidence: float
    ) -> List[Dict]:
        """
        开采单日候选样本
        
        Args:
            stock_code: 股票代码
            date_str: 日期 (YYYY-MM-DD)
            min_confidence: 最小置信度阈值
            
        Returns:
            当日候选样本列表
        """
        candidates = []
        
        # 使用QMT获取当日Tick数据
        try:
            provider = QMTHistoricalProvider(
                stock_code=stock_code,
                start_time=f"{date_str.replace('-', '')}093000",
                end_time=f"{date_str.replace('-', '')}150000",
                period="tick"
            )
            
            # 收集当日所有Tick
            ticks = []
            for tick in provider.iter_ticks():
                ticks.append(tick)
            
            if len(ticks) < 20:  # 数据不足
                return candidates
            
            # 滑动窗口检测（每5分钟一个窗口）
            window_size = 20  # 20个tick点
            step_size = 10    # 步长10个点
            
            for i in range(0, len(ticks) - window_size, step_size):
                window_ticks = ticks[i:i+window_size]
                
                # 构建当前tick数据
                current_tick = window_ticks[-1]
                tick_data = {
                    'stock_code': stock_code,
                    'datetime': datetime.fromtimestamp(current_tick['time'] / 1000),
                    'price': current_tick['last_price'],
                    'volume': current_tick['volume'],
                    'amount': current_tick.get('amount', 0),
                }
                
                # 构建上下文（价格/成交量历史）
                price_history = [t['last_price'] for t in window_ticks]
                volume_history = [t['volume'] for t in window_ticks]
                
                context = {
                    'price_history': price_history,
                    'volume_history': volume_history,
                    'ma5': sum(price_history[-5:]) / 5 if len(price_history) >= 5 else price_history[-1],
                    'ma20': sum(price_history) / len(price_history),
                }
                
                # 使用统一战法核心检测
                events = self.warfare_core.process_tick(tick_data, context)
                
                # 筛选Halfway Breakout事件
                halfway_events = [e for e in events if e['event_type'] == 'halfway_breakout']
                
                for event in halfway_events:
                    if event['confidence'] >= min_confidence:
                        # 记录候选样本
                        candidate = {
                            'stock_code': stock_code,
                            'date': date_str,
                            'time': datetime.fromtimestamp(current_tick['time'] / 1000).strftime("%H:%M:%S"),
                            'price_series': price_history,
                            'volume_series': volume_history,
                            'trigger_price': current_tick['last_price'],
                            'confidence': event['confidence'],
                            'description': event['description'],
                            'detected_by': 'unified_warfare_core',
                            'label': None,  # 待人工标注
                            'label_reason': None,  # 标注理由
                            'mined_at': datetime.now().isoformat(),
                        }
                        candidates.append(candidate)
            
        except Exception as e:
            logger.error(f"获取{stock_code} {date_str}数据失败: {e}")
        
        return candidates
    
    def save_candidates(self, candidates: List[Dict], filename: str = None):
        """
        保存候选样本到文件
        
        Args:
            candidates: 候选样本列表
            filename: 文件名（默认为时间戳）
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"halfway_candidates_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 候选样本已保存: {filepath}")
        logger.info(f"   - 样本数量: {len(candidates)}")
    
    def load_candidates(self, filename: str) -> List[Dict]:
        """
        从文件加载候选样本
        
        Args:
            filename: 文件名
            
        Returns:
            候选样本列表
        """
        filepath = self.output_dir / filename
        
        with open(filepath, 'r', encoding='utf-8') as f:
            candidates = json.load(f)
        
        logger.info(f"📂 已加载候选样本: {filepath}")
        logger.info(f"   - 样本数量: {len(candidates)}")
        
        return candidates
    
    def annotate_sample(
        self,
        candidate: Dict,
        label: str,  # 'positive', 'negative', 'uncertain'
        reason: str
    ) -> Dict:
        """
        人工标注单个样本
        
        Args:
            candidate: 候选样本
            label: 标签 ('positive', 'negative', 'uncertain')
            reason: 标注理由
            
        Returns:
            标注后的样本
        """
        candidate['label'] = label
        candidate['label_reason'] = reason
        candidate['annotated_at'] = datetime.now().isoformat()
        
        return candidate
    
    def export_labeled_samples(
        self,
        candidates: List[Dict],
        output_file: str = "tests/real_samples/halfway_labeled_samples.json"
    ):
        """
        导出已标注样本到测试目录
        
        Args:
            candidates: 候选样本列表（含标注）
            output_file: 输出文件路径
        """
        # 筛选已标注的样本
        labeled = [c for c in candidates if c.get('label') is not None]
        
        if not labeled:
            logger.warning("⚠️ 没有已标注的样本可导出")
            return
        
        output_path = PROJECT_ROOT / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(labeled, f, ensure_ascii=False, indent=2)
        
        # 统计
        positive = len([c for c in labeled if c['label'] == 'positive'])
        negative = len([c for c in labeled if c['label'] == 'negative'])
        uncertain = len([c for c in labeled if c['label'] == 'uncertain'])
        
        logger.info(f"✅ 已导出标注样本: {output_path}")
        logger.info(f"   - 正样本: {positive}")
        logger.info(f"   - 负样本: {negative}")
        logger.info(f"   - 不确定: {uncertain}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='半路突破样本开采器')
    parser.add_argument('--mode', choices=['mine', 'annotate', 'export'], 
                       default='mine', help='运行模式')
    parser.add_argument('--stocks', type=str, help='股票代码文件路径')
    parser.add_argument('--start-date', type=str, 
                       default=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
                       help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       default=datetime.now().strftime("%Y-%m-%d"),
                       help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--min-confidence', type=float, default=0.3,
                       help='最小置信度阈值')
    parser.add_argument('--input', type=str, help='输入文件（用于annotate/export模式）')
    parser.add_argument('--output', type=str, help='输出文件')
    
    args = parser.parse_args()
    
    # 初始化开采器
    miner = HalfwaySampleMiner()
    
    if args.mode == 'mine':
        # 加载股票列表
        if args.stocks:
            with open(args.stocks, 'r') as f:
                stock_codes = [line.strip() for line in f if line.strip()]
        else:
            # 默认使用热门股列表
            hot_stocks_path = PROJECT_ROOT / "config" / "hot_stocks.json"
            with open(hot_stocks_path, 'r') as f:
                stock_codes = json.load(f)
            # 只取前20只做试点
            stock_codes = stock_codes[:20]
        
        logger.info(f"🎯 开始开采模式")
        logger.info(f"   - 股票数: {len(stock_codes)}")
        logger.info(f"   - 日期: {args.start_date} 至 {args.end_date}")
        
        # 执行开采
        candidates = miner.mine_candidates(
            stock_codes=stock_codes,
            start_date=args.start_date,
            end_date=args.end_date,
            min_confidence=args.min_confidence
        )
        
        # 保存候选
        if candidates:
            miner.save_candidates(candidates, args.output)
            logger.info(f"\n💡 下一步: 人工复核候选样本并标注")
            logger.info(f"   候选文件位置: {miner.output_dir}/")
        else:
            logger.warning("⚠️ 未发现候选样本，尝试降低置信度阈值或扩大日期范围")
    
    elif args.mode == 'annotate':
        # 标注模式（简化版，实际应开发Web界面或CLI交互工具）
        logger.info("📝 标注模式")
        logger.info("   提示：当前为简化CLI版本，建议开发Web标注工具提升效率")
        
        if not args.input:
            logger.error("❌ 请指定输入文件: --input <候选文件.json>")
            return
        
        candidates = miner.load_candidates(args.input)
        
        # 交互式标注
        for i, candidate in enumerate(candidates):
            if candidate.get('label') is not None:
                continue  # 已标注，跳过
            
            print(f"\n{'='*80}")
            print(f"样本 {i+1}/{len(candidates)}: {candidate['stock_code']} {candidate['date']} {candidate['time']}")
            print(f"置信度: {candidate['confidence']:.2f}")
            print(f"描述: {candidate['description']}")
            print(f"价格序列(前5): {candidate['price_series'][:5]}")
            print(f"价格序列(后5): {candidate['price_series'][-5:]}")
            print(f"\n选项: 1=正样本(positive) 2=负样本(negative) 3=不确定(uncertain) s=跳过 q=退出")
            
            choice = input("选择: ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == 's':
                continue
            elif choice in ['1', 'positive']:
                reason = input("标注理由: ").strip()
                miner.annotate_sample(candidate, 'positive', reason)
            elif choice in ['2', 'negative']:
                reason = input("标注理由(如'假突破'/'无量上涨'等): ").strip()
                miner.annotate_sample(candidate, 'negative', reason)
            elif choice in ['3', 'uncertain']:
                reason = input("不确定理由: ").strip()
                miner.annotate_sample(candidate, 'uncertain', reason)
        
        # 保存标注结果
        output_file = args.input.replace('.json', '_labeled.json')
        miner.save_candidates(candidates, output_file)
    
    elif args.mode == 'export':
        # 导出已标注样本到测试目录
        if not args.input:
            logger.error("❌ 请指定输入文件: --input <已标注文件.json>")
            return
        
        candidates = miner.load_candidates(args.input)
        miner.export_labeled_samples(candidates, args.output)


if __name__ == "__main__":
    main()