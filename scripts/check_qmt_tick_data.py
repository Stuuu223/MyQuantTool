#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查QMT Tick数据 - 诊断竞价快照保存率为0的原因

Author: MyQuantTool Team
Date: 2026-02-11
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from xtquant import xtdata
from logic.logger import get_logger

logger = get_logger(__name__)


def main():
    print('=' * 80)
    print('🔍 检查QMT Tick数据')
    print('=' * 80)

    # 测试获取几只热门股票的Tick数据
    test_stocks = ['000001.SZ', '002555.SZ', '600519.SH']

    print('\n📊 获取Tick数据:')

    for code in test_stocks:
        tick_data = xtdata.get_full_tick([code])

        print(f'\n{code}:')
        print(f'   返回类型: {type(tick_data)}')

        if isinstance(tick_data, dict):
            tick = tick_data.get(code, {})
            keys_msg = list(tick.keys()) if tick else '空字典'
            print(f'   Tick数据键: {keys_msg}')

            if tick:
                # 检查各种可能的字段名
                volume = (
                    tick.get('totalVolume') or
                    tick.get('volume') or
                    tick.get('total_volume') or
                    0
                )
                amount = tick.get('amount', 0)
                last_price = tick.get('lastPrice', 0)

                print(f'   成交量(volume): {volume}')
                print(f'   成交额(amount): {amount}')
                print(f'   最新价(lastPrice): {last_price}')

                # 判断是否会被保存
                if volume > 0 or amount > 0:
                    print(f'   ✅ 符合保存条件 (volume={volume}, amount={amount})')
                else:
                    print(f'   ❌ 不符合保存条件 (volume={volume}, amount={amount})')
            else:
                print(f'   ❌ Tick数据为空')
        else:
            print(f'   ❌ 返回数据格式异常: {tick_data}')

    print('\n' + '=' * 80)


if __name__ == "__main__":
    main()