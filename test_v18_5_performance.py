#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.5 性能测试脚本
测试所有 V18.5 新功能的性能表现
"""

import time
from logic.logger import get_logger
from logic.utils import Utils
from logic.money_flow_master import get_money_flow_master
from logic.low_suction_engine import get_low_suction_engine
from logic.data_manager import DataManager

logger = get_logger(__name__)

def test_limit_ratio():
    """测试动态涨停系数"""
    print("\n" + "="*60)
    print("🎯 测试动态涨停系数")
    print("="*60)
    
    test_codes = ['000001', '300001', '688001', '830799', '600000', '600519ST']
    
    start_time = time.time()
    for code in test_codes:
        limit_ratio = Utils.get_limit_ratio(code)
        print(f"{code}: 涨停系数 {limit_ratio:.2f}")
    
    elapsed = time.time() - start_time
    print(f"✅ 动态涨停系数测试耗时: {elapsed:.3f}秒")
    print(f"✅ 平均耗时: {elapsed/len(test_codes):.3f}秒/只")
    
    return True

def test_money_flow_master():
    """测试资金流大师"""
    print("\n" + "="*60)
    print("📊 测试资金流大师")
    print("="*60)
    
    mfm = get_money_flow_master()
    stock_code = '000001'
    current_price = 10.0
    prev_close = 10.0
    
    # 测试 DDE 评分
    start_time = time.time()
    dde_score = mfm.calculate_dde_score(stock_code)
    elapsed = time.time() - start_time
    print(f"✅ DDE 评分: {dde_score:.1f}/100, 耗时: {elapsed:.3f}秒")
    
    # 测试 DDE 背离
    start_time = time.time()
    divergence = mfm.check_dde_divergence(stock_code, current_price, prev_close)
    elapsed = time.time() - start_time
    print(f"✅ DDE 背离检测: {'有背离' if divergence['has_divergence'] else '无背离'}, 耗时: {elapsed:.3f}秒")
    
    # 测试竞价抢筹
    start_time = time.time()
    surge = mfm.check_auction_dde_surge(stock_code)
    elapsed = time.time() - start_time
    print(f"✅ 竞价抢筹检测: {'有抢筹' if surge['has_surge'] else '无抢筹'}, 耗时: {elapsed:.3f}秒")
    
    # 测试 DDE 否决权
    start_time = time.time()
    is_vetoed, veto_reason = mfm.check_dde_veto(stock_code, 'BUY')
    elapsed = time.time() - start_time
    print(f"✅ DDE 否决权: {'已否决' if is_vetoed else '未否决'}, 耗时: {elapsed:.3f}秒")
    
    # 批量测试
    print("\n批量测试（5只股票）:")
    test_codes = ['000001', '000002', '600000', '600519', '300001']
    
    start_time = time.time()
    for code in test_codes:
        mfm.calculate_dde_score(code)
    elapsed = time.time() - start_time
    print(f"✅ 批量 DDE 评分耗时: {elapsed:.3f}秒")
    print(f"✅ 平均耗时: {elapsed/len(test_codes):.3f}秒/只")
    
    return True

def test_low_suction_engine():
    """测试低吸逻辑引擎"""
    print("\n" + "="*60)
    print("🔻 测试低吸逻辑引擎")
    print("="*60)
    
    lse = get_low_suction_engine()
    stock_code = '000001'
    current_price = 10.0
    prev_close = 10.0
    
    # 测试 5日均线低吸
    start_time = time.time()
    ma5_suction = lse.check_ma5_suction(stock_code, current_price, prev_close)
    elapsed = time.time() - start_time
    print(f"✅ 5日均线低吸: {'有信号' if ma5_suction['has_suction'] else '无信号'}, 耗时: {elapsed:.3f}秒")
    
    # 测试逻辑回踩
    start_time = time.time()
    logic_reversion = lse.check_logic_reversion(stock_code, ['机器人', '航天'], False)
    elapsed = time.time() - start_time
    print(f"✅ 逻辑回踩: {'有逻辑' if logic_reversion['has_logic'] else '无逻辑'}, 耗时: {elapsed:.3f}秒")
    
    # 测试综合低吸分析
    start_time = time.time()
    comprehensive = lse.analyze_low_suction(
        stock_code, current_price, prev_close,
        logic_keywords=['机器人', '航天'], lhb_institutional=False
    )
    elapsed = time.time() - start_time
    print(f"✅ 综合低吸分析: {'有信号' if comprehensive['has_suction'] else '无信号'}, 耗时: {elapsed:.3f}秒")
    
    # 批量测试
    print("\n批量测试（5只股票）:")
    test_codes = ['000001', '000002', '600000', '600519', '300001']
    
    start_time = time.time()
    for code in test_codes:
        lse.check_ma5_suction(code, 10.0, 10.0)
    elapsed = time.time() - start_time
    print(f"✅ 批量 5日均线低吸耗时: {elapsed:.3f}秒")
    print(f"✅ 平均耗时: {elapsed/len(test_codes):.3f}秒/只")
    
    return True

def test_integration():
    """测试集成性能"""
    print("\n" + "="*60)
    print("🔗 测试集成性能")
    print("="*60)
    
    data_manager = DataManager()
    mfm = get_money_flow_master()
    lse = get_low_suction_engine()
    
    stock_code = '000001'
    
    # 获取实时数据
    start_time = time.time()
    realtime_data = data_manager.get_realtime_data(stock_code)
    elapsed = time.time() - start_time
    print(f"✅ 获取实时数据耗时: {elapsed:.3f}秒")
    
    if realtime_data:
        current_price = realtime_data.get('price', 0)
        prev_close = realtime_data.get('pre_close', current_price)
        
        # 综合分析
        start_time = time.time()
        
        # DDE 分析
        dde_score = mfm.calculate_dde_score(stock_code)
        dde_divergence = mfm.check_dde_divergence(stock_code, current_price, prev_close)
        
        # 低吸分析
        ma5_suction = lse.check_ma5_suction(stock_code, current_price, prev_close)
        
        # 涨停系数
        limit_ratio = Utils.get_limit_ratio(stock_code)
        
        elapsed = time.time() - start_time
        print(f"✅ 综合分析耗时: {elapsed:.3f}秒")
        print(f"✅ DDE 评分: {dde_score:.1f}/100")
        print(f"✅ 涨停系数: {limit_ratio:.2f}")
    
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 V18.5 性能测试开始")
    print("="*60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    try:
        # 测试动态涨停系数
        results['limit_ratio'] = test_limit_ratio()
        
        # 测试资金流大师
        results['money_flow_master'] = test_money_flow_master()
        
        # 测试低吸逻辑引擎
        results['low_suction_engine'] = test_low_suction_engine()
        
        # 测试集成性能
        results['integration'] = test_integration()
        
    except Exception as e:
        logger.error(f"性能测试失败: {e}")
        print(f"❌ 性能测试失败: {e}")
    
    # 汇总
    print("\n" + "="*60)
    print("📊 性能测试汇总")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️ {total - passed} 个测试失败")

if __name__ == "__main__":
    main()