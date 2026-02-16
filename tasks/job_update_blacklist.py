#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V16.4.0 黑名单生成器（生产级）

功能：
1. 获取最近7天全市场公告
2. 关键词过滤：['立案', '调查', 'ST', '违规', '处罚', '退市风险']
3. 生成 data/risk/blacklist.json
4. 更新 data/system_state.json

执行频率：每天08:30（盘前）
耗时：约100-150秒（500只股票，含安全延迟）

安全机制：
- 使用RateLimiter全局限流
- 随机延迟（防WAF指纹识别）
- 只扫描高风险股票（ST+异常波动）

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.4.0
"""

import sys
import os
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("[job_update_blacklist] ⚠️ akshare 未安装")

from logic.utils.logger import get_logger
from logic.core.rate_limiter import get_rate_limiter

logger = get_logger(__name__)

# 风险关键词（保守策略）
RISK_KEYWORDS = ['立案', '调查', 'ST', '违规', '处罚', '退市风险', '停牌核查']

# 系统状态文件路径
SYSTEM_STATE_FILE = Path('data/system_state.json')
BLACKLIST_FILE = Path('data/risk/blacklist.json')


def update_system_state(blacklist_count: int):
    """
    更新系统状态（解决"失忆"问题）

    Args:
        blacklist_count: 黑名单股票数量
    """
    state = {
        'last_blacklist_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'blacklist_count': blacklist_count,
        'risk_stocks_version': 'v16.4',
        'update_timestamp': time.time()
    }

    SYSTEM_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SYSTEM_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ 系统状态已更新: {state}")
    return state


def load_system_state():
    """加载系统状态"""
    if not SYSTEM_STATE_FILE.exists():
        return None

    try:
        with open(SYSTEM_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ 加载系统状态失败: {e}")
        return None


def update_blacklist():
    """
    更新黑名单（主函数）

    流程：
    1. 获取A股列表
    2. 筛选高风险股票（ST+异常波动）
    3. 循环查询公告（含安全延迟）
    4. 关键词过滤
    5. 生成黑名单文件
    6. 更新系统状态
    """
    print("=" * 80)
    print("🚨 V16.4.0 黑名单生成器（生产级）")
    print("=" * 80)

    # 读取系统状态
    state = load_system_state()
    if state:
        print(f"📋 上次更新: {state.get('last_blacklist_update', '未知')}")
        print(f"📊 上次数量: {state.get('blacklist_count', 0)} 只")

    # 计算时间范围（最近7天）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    print(f"⏰ 扫描时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

    if not AKSHARE_AVAILABLE:
        print("❌ AkShare 不可用，无法更新黑名单")
        return []

    blacklist = []

    try:
        # 获取全市场股票列表
        print("📋 获取A股列表...")
        stock_list = ak.stock_zh_a_spot_em()
        print(f"✅ 获取到 {len(stock_list)} 只股票")

        # 筛选高风险股票（优化性能）
        print("🔍 筛选高风险股票...")
        focus_stocks = []

        for _, row in stock_list.iterrows():
            code = row['代码']
            name = row['名称']
            change_pct = abs(row['涨跌幅'])
            change_pct_raw = row['涨跌幅']

            # 策略1: ST股票强制检查
            if 'ST' in name or '*ST' in name:
                focus_stocks.append((code, name, 'ST股'))
            # 策略2: 异常波动股票（可能有利空）
            elif change_pct > 5:
                focus_stocks.append((code, name, f'异常波动{change_pct:.1f}%'))
            # V16.4.0 补丁: 策略3: 阴跌股票（防止阴跌出雷）
            elif change_pct_raw < -2:  # 跌幅超过2%
                focus_stocks.append((code, name, f'阴跌{change_pct_raw:.1f}%'))

        print(f"🎯 聚焦扫描 {len(focus_stocks)} 只高风险股票...")

        # 获取全局限流器
        limiter = get_rate_limiter()

        # 循环查询公告（带安全延迟）
        print(f"🔍 开始扫描公告（关键词: {RISK_KEYWORDS}）...")

        for idx, (code, name, reason) in enumerate(focus_stocks):
            try:
                # V16.4.0: 安全延迟（防WAF）
                time.sleep(random.uniform(0.1, 0.3))

                # V16.4.0: 限流器检查
                limiter.wait_if_needed(url="akshare_disclosure")
                limiter.record_request(url="akshare_disclosure")

                # 获取该股票最近7天的公告
                df = ak.stock_zh_a_disclosure_report_cninfo(
                    symbol=code,
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d')
                )

                if df.empty:
                    continue

                # 检查公告标题
                for _, ann in df.iterrows():
                    title = str(ann['公告标题'])
                    if any(keyword in title for keyword in RISK_KEYWORDS):
                        blacklist.append({
                            'code': code,
                            'name': name,
                            'title': title,
                            'date': str(ann['公告时间']),
                            'reason': reason
                        })
                        logger.warning(f"⛔ 发现风险公告: {code} {name} - {title}")
                        break  # 一只股票只记录一次

                # 进度显示
                if (idx + 1) % 10 == 0:
                    print(f"  进度: {idx + 1}/{len(focus_stocks)}")

            except Exception as e:
                logger.debug(f"⚠️ 跳过 {code}: {e}")
                continue

    except Exception as e:
        logger.error(f"❌ 获取公告失败: {e}")
        # 失败时至少保留 ST 股票黑名单
        try:
            stock_list = ak.stock_zh_a_spot_em()
            for _, row in stock_list.iterrows():
                name = row['名称']
                if 'ST' in name or '*ST' in name or '退' in name:
                    blacklist.append({
                        'code': row['代码'],
                        'name': name,
                        'title': 'ST或退市股票',
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'reason': '基础风控'
                    })
        except:
            pass

    # 保存黑名单
    BLACKLIST_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'count': len(blacklist),
            'stocks': blacklist
        }, f, ensure_ascii=False, indent=2)

    # 更新系统状态
    update_system_state(len(blacklist))

    print("=" * 80)
    print(f"✅ 黑名单已更新: {BLACKLIST_FILE}")
    print(f"📊 黑名单数量: {len(blacklist)} 只")

    if blacklist:
        print("\n⛔ 黑名单股票:")
        for item in blacklist[:10]:  # 只显示前10只
            print(f"  - {item['code']} {item['name']}: {item['title']}")

    print("=" * 80)

    return blacklist


if __name__ == "__main__":
    try:
        blacklist = update_blacklist()
        print(f"\n✅ 黑名单更新完成: {len(blacklist)} 只")
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)