#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短线活跃股生成脚本 (AkShare 版本 - 带速率限制)

使用 AkShare 获取日线数据，筛选出 500 只短线最活跃的股票

筛选条件：
- 日均换手率 > 3% (活跃)
- 近 60 天有涨停 (有妖气)
- 日均成交额 < 50亿 (剔除超级大象)
- 剔除停牌股票

防封机制：
- 集成 RateLimiter 速率限制器
- 使用 safe_request 包装 API 调用
- 推荐间隔：3-5 秒（历史日线数据）
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import time

# 禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger
from logic.rate_limiter import get_rate_limiter, safe_request
from logic.api_robust import robust_api_call

logger = get_logger("generate_active_pool_akshare")


@robust_api_call(max_retries=3, delay=2, return_empty_df=True)
def get_stock_history_safe(code):
    """
    安全获取股票历史数据（带重试和速率限制）
    """
    import akshare as ak
    
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
    
    df = ak.stock_zh_a_hist(
        symbol=code.replace('.SH', '').replace('.SZ', ''),
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"  # 前复权
    )
    
    return df


def generate_active_pool():
    """
    使用 AkShare 生成短线活跃股名单（带速率限制）
    """
    logger.info("=" * 80)
    logger.info("🔍 开始生成短线活跃股名单 (AkShare 版本 + 速率限制)")
    logger.info("=" * 80)
    
    # 获取速率限制器
    limiter = get_rate_limiter()
    limiter.print_stats()
    
    # 获取全市场股票列表
    logger.info("   📋 获取全市场股票列表...")
    try:
        import akshare as ak
        import requests
        
        # 创建 session 并禁用代理
        session = requests.Session()
        session.trust_env = False  # 不信任系统代理设置
        session.proxies = {'http': None, 'https': None}
        
        # 使用 safe_request 包装
        stock_list = safe_request(
            lambda: ak.stock_zh_a_spot_em()
        )
        logger.info(f"   ✅ 获取到 {len(stock_list)} 只股票")
    except Exception as e:
        logger.error(f"❌ 获取股票列表失败: {e}")
        logger.info("   尝试使用备用方法...")
        try:
            # 备用方法：直接使用 requests 获取
            import requests
            url = "http://82.push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': 1, 'pz': 5000, 'po': 1, 'np': 1,
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': 2, 'invt': 2,
                'fid': 'f12',
                'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048',
                'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152'
            }
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            if 'data' in data and 'diff' in data['data']:
                df = pd.DataFrame(data['data']['diff'])
                logger.info(f"   ✅ 备用方法获取到 {len(df)} 只股票")
                stock_list = df
            else:
                raise Exception("备用方法也失败了")
        except Exception as e2:
            logger.error(f"❌ 备用方法也失败: {e2}")
            return []
    
    # 等待速率限制器
    limiter.wait_if_needed()
    
    # 筛选条件
    # 1. 剔除停牌 (成交额为0)
    stock_list = stock_list[stock_list['成交额'] > 0]
    
    # 2. 剔除大市值 (成交额 > 50亿)
    stock_list = stock_list[stock_list['成交额'] < 50e8]
    
    logger.info(f"   筛选后剩余: {len(stock_list)} 只")
    
    # 获取每只股票的日线数据
    valid_stocks = []
    skipped_reasons = {
        '换手率低': 0,
        '无涨停': 0,
        '数据不足': 0,
        '其他': 0
    }
    
    # 为了加快速度，我们先按换手率排序，只处理前 1000 只
    # 因为高换手率的股票更可能符合我们的条件
    stock_list_sorted = stock_list.sort_values('换手率', ascending=False).head(1000)
    
    logger.info(f"   开始处理前 1000 只高换手率股票...")
    logger.info(f"   ⚠️  速率限制：每分钟最多 {limiter.max_per_minute} 次请求")
    logger.info(f"   ⏱️  预计耗时：约 {1000 * 4 / 60:.0f} 分钟")
    
    for idx, row in stock_list_sorted.iterrows():
        code = row['代码']
        name = row['名称']
        current_turn = row['换手率']
        current_amount = row['成交额']
        
        # 等待速率限制器
        limiter.wait_if_needed()
        
        try:
            # 获取近 60 天日线数据（使用安全包装）
            df = get_stock_history_safe(code)
            
            if df is None or len(df) < 20:
                skipped_reasons['数据不足'] += 1
                continue
            
            # 计算指标
            # 1. 日均换手率 (最近 20 天)
            avg_turn = df['换手率'].tail(20).mean()
            
            # 2. 检查是否有涨停
            # 简单判断：涨幅 >= 9.5%
            has_limit = (df['涨跌幅'] >= 9.5).any()
            
            # 3. 日均成交额
            avg_amount = df['成交量'].tail(20).mean() * df['收盘'].tail(20).mean()  # 粗略估算
            
            # 筛选逻辑
            if avg_turn > 3.0 and has_limit and avg_amount < 50e8:
                valid_stocks.append({
                    'code': code,
                    'name': name,
                    'avg_turn': round(avg_turn, 2),
                    'has_limit': has_limit,
                    'avg_amount': round(avg_amount / 1e8, 2),  # 亿元
                    'last_price': round(row['最新价'], 2),
                    'pct_change': round(row['涨跌幅'], 2)
                })
            else:
                if avg_turn <= 3.0:
                    skipped_reasons['换手率低'] += 1
                elif not has_limit:
                    skipped_reasons['无涨停'] += 1
                elif avg_amount >= 50e8:
                    skipped_reasons['其他'] += 1
        
        except Exception as e:
            logger.debug(f"   跳过 {code} ({name}): {e}")
            skipped_reasons['其他'] += 1
            continue
        
        # 显示进度
        if (idx + 1) % 50 == 0:
            logger.info(f"   进度: {idx + 1}/{len(stock_list_sorted)}, 已筛选: {len(valid_stocks)} 只")
            limiter.print_stats()
    
    # 排序：按换手率倒序
    valid_stocks.sort(key=lambda x: x['avg_turn'], reverse=True)
    
    # 取 Top 500
    top_500 = valid_stocks[:500]
    
    logger.info("=" * 80)
    logger.info(f"✅ 筛选完成！入选 {len(top_500)} 只")
    logger.info("=" * 80)
    logger.info(f"跳过原因统计:")
    for reason, count in skipped_reasons.items():
        logger.info(f"   - {reason}: {count} 只")
    
    logger.info(f"\n榜喾示例 (Top 20):")
    for i, stock in enumerate(top_500[:20]):
        logger.info(f"   {i+1}. {stock['code']} {stock['name']} | 换手率: {stock['avg_turn']}% | 涨停: {'是' if stock['has_limit'] else '否'} | 成交额: {stock['avg_amount']}亿 | 涨幅: {stock['pct_change']}%")
    
    # 保存为 JSON (两种格式)
    output_dir = PROJECT_ROOT / 'config'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 格式 1：仅代码列表
    code_list_file = output_dir / 'active_stocks.json'
    code_list = [stock['code'] for stock in top_500]
    with open(code_list_file, 'w', encoding='utf-8') as f:
        json.dump(code_list, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 代码列表已保存至: {code_list_file}")
    
    # 格式 2：详细信息
    detail_file = output_dir / 'active_stocks_detail.json'
    with open(detail_file, 'w', encoding='utf-8') as f:
        json.dump(top_500, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 详细信息已保存至: {detail_file}")
    
    # 打印最终统计
    logger.info("=" * 80)
    logger.info("📊 速率限制统计")
    logger.info("=" * 80)
    limiter.print_stats()
    
    return code_list


if __name__ == "__main__":
    result = generate_active_pool()
    
    if result:
        logger.info("=" * 80)
        logger.info(f"🎉 成功生成 {len(result)} 只短线活跃股！")
        logger.info("=" * 80)
        logger.info("请查看以下文件:")
        logger.info("  - config/active_stocks.json (代码列表)")
        logger.info("  - config/active_stocks_detail.json (详细信息)")
    else:
        logger.error("❌ 生成失败")