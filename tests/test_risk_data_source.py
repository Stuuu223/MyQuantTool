#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V16.4.0 风险数据源测试

测试目标：
1. 验证Tushare anns接口性能
2. 验证AkShare公告接口性能
3. 确定最优的黑名单生成方案

Usage:
    python tests/test_risk_data_source.py

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.4.0
"""

import sys
import os
import time
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Tushare Token（8000积分）
TUSHARE_TOKEN = '1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b'

# 风险关键词
RISK_KEYWORDS = ['立案', '调查', 'ST', '违规', '处罚', '退市']


def test_tushare_anns():
    """
    测试Tushare anns接口（全量查询）

    Returns:
        dict: 测试结果
    """
    print("=" * 80)
    print("测试1: Tushare anns接口（全量查询）")
    print("=" * 80)

    try:
        import tushare as ts

        # 设置Token
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()

        # 计算时间范围（最近7天）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        print(f"⏰ 时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

        # 开始计时
        start_time = time.time()

        # 调用anns_d接口
        df = pro.anns_d(
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )

        end_time = time.time()
        elapsed_time = end_time - start_time

        print(f"✅ 查询成功")
        print(f"📊 公告总数: {len(df)} 条")
        print(f"⏱️ 耗时: {elapsed_time:.2f} 秒")

        # 检查字段
        print(f"📋 字段: {list(df.columns)}")

        # 关键词过滤
        blacklist = []
        for _, row in df.iterrows():
            title = row['ann_title']
            if any(keyword in title for keyword in RISK_KEYWORDS):
                blacklist.append({
                    'code': row['ts_code'],
                    'name': '',  # Tushare不返回名称
                    'title': title,
                    'date': row['ann_date']
                })

        print(f"⛔ 发现风险公告: {len(blacklist)} 条")

        if blacklist:
            print("\n前10条风险公告:")
            for item in blacklist[:10]:
                print(f"  - {item['code']}: {item['title']}")

        return {
            'success': True,
            'elapsed_time': elapsed_time,
            'total_announcements': len(df),
            'risk_count': len(blacklist),
            'data_source': 'Tushare anns'
        }

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'data_source': 'Tushare anns'
        }


def test_akshare_fullmarket():
    """
    测试AkShare全市场查询（如果不传symbol）

    Returns:
        dict: 测试结果
    """
    print("\n" + "=" * 80)
    print("测试2: AkShare全市场查询（不传symbol）")
    print("=" * 80)

    try:
        import akshare as ak

        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        print(f"⏰ 时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

        # 开始计时
        start_time = time.time()

        # 尝试不传symbol
        try:
            df = ak.stock_zh_a_disclosure_report_cninfo(
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )
        except TypeError as e:
            # 如果不支持不传symbol，测试传空字符串
            print(f"⚠️ 不传symbol失败，尝试空字符串: {e}")
            df = ak.stock_zh_a_disclosure_report_cninfo(
                symbol='',
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )

        end_time = time.time()
        elapsed_time = end_time - start_time

        print(f"✅ 查询成功")
        print(f"📊 公告总数: {len(df)} 条")
        print(f"⏱️ 耗时: {elapsed_time:.2f} 秒")

        return {
            'success': True,
            'elapsed_time': elapsed_time,
            'total_announcements': len(df),
            'data_source': 'AkShare (full market)'
        }

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'data_source': 'AkShare (full market)'
        }


def test_akshare_loop():
    """
    测试AkShare循环查询（必须传symbol）

    Returns:
        dict: 测试结果
    """
    print("\n" + "=" * 80)
    print("测试3: AkShare循环查询（测试50只股票）")
    print("=" * 80)

    try:
        import akshare as ak

        # 获取股票列表
        print("📋 获取股票列表...")
        stock_list = ak.stock_zh_a_spot_em()

        # 只测试前50只
        test_stocks = stock_list.head(50)
        test_codes = test_stocks['代码'].tolist()

        print(f"📊 测试股票数量: {len(test_codes)} 只")

        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        print(f"⏰ 时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

        # 开始计时
        start_time = time.time()

        # 循环查询
        success_count = 0
        error_count = 0
        total_announcements = 0

        for i, code in enumerate(test_codes):
            try:
                df = ak.stock_zh_a_disclosure_report_cninfo(
                    symbol=code,
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d')
                )
                success_count += 1
                total_announcements += len(df)
            except Exception as e:
                error_count += 1

            # 打印进度
            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{len(test_codes)}")

        end_time = time.time()
        elapsed_time = end_time - start_time
        avg_time_per_stock = elapsed_time / len(test_codes)

        print(f"✅ 测试完成")
        print(f"📊 成功: {success_count}, 失败: {error_count}")
        print(f"📊 公告总数: {total_announcements} 条")
        print(f"⏱️ 总耗时: {elapsed_time:.2f} 秒")
        print(f"⏱️ 平均每只股票: {avg_time_per_stock:.2f} 秒")
        print(f"📊 预估500只股票耗时: {avg_time_per_stock * 500:.0f} 秒 ({avg_time_per_stock * 500 / 60:.1f} 分钟)")

        return {
            'success': True,
            'elapsed_time': elapsed_time,
            'avg_time_per_stock': avg_time_per_stock,
            'estimated_500_stocks': avg_time_per_stock * 500,
            'total_announcements': total_announcements,
            'data_source': 'AkShare (loop)'
        }

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'data_source': 'AkShare (loop)'
        }


def main():
    """主函数"""
    print("=" * 80)
    print("V16.4.0 风险数据源测试")
    print("=" * 80)
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []

    # 测试1: Tushare anns接口
    result1 = test_tushare_anns()
    results.append(result1)

    # 测试2: AkShare全市场查询
    result2 = test_akshare_fullmarket()
    results.append(result2)

    # 测试3: AkShare循环查询
    result3 = test_akshare_loop()
    results.append(result3)

    # 汇总结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)

    for i, result in enumerate(results, 1):
        print(f"\n测试{i}: {result['data_source']}")
        if result['success']:
            print(f"  ✅ 成功")
            if 'elapsed_time' in result:
                print(f"  ⏱️ 耗时: {result['elapsed_time']:.2f} 秒")
            if 'total_announcements' in result:
                print(f"  📊 公告数: {result['total_announcements']}")
            if 'risk_count' in result:
                print(f"  ⛔ 风险公告: {result['risk_count']}")
            if 'estimated_500_stocks' in result:
                print(f"  📊 预估500只: {result['estimated_500_stocks']:.0f} 秒")
        else:
            print(f"  ❌ 失败: {result['error']}")

    # 推荐方案
    print("\n" + "=" * 80)
    print("💡 推荐方案")
    print("=" * 80)

    tushare_available = results[0]['success']
    akshare_fullmarket = results[1]['success']
    akshare_loop = results[2]['success']

    if tushare_available:
        print("✅ 推荐: 使用 Tushare anns 接口（全量查询，速度快）")
    elif akshare_fullmarket:
        print("⚠️  推荐: 使用 AkShare 全市场查询（需要验证数据质量）")
    elif akshare_loop:
        print("⚠️  推荐: 使用 AkShare 循环查询（性能较差，需要限制查询范围）")
    else:
        print("❌ 所有方案均不可用，需要重新设计")

    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
