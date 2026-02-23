#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V18核心死律修复单元测试

测试内容:
1. P11-A2: final_score不为0（废除Sustain乘数，改为扣分制）
2. P11-A3: 基础分高分辨率（线性极值映射）
3. P11-A4: VWAP惩罚生效（非乘数）

Author: AI架构师
Date: 2026-02-23
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from holographic_backtest_v2 import HolographicBacktestEngine


class V18FixTests(unittest.TestCase):
    """V18修复验证测试"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.engine = HolographicBacktestEngine('20251231')
        print("\n" + "="*80)
        print("V18核心死律修复验证测试")
        print("="*80)
    
    def test_01_sustain_penalty_not_multiplier(self):
        """
        P11-A2: 测试Sustain从乘数改为惩罚扣分制
        
        旧逻辑: final_score = base * multiplier * (sustain/100)  -> sustain=0时结果为0
        新逻辑: final_score = base * multiplier - sustain_penalty  -> sustain=0时扣分但不为0
        """
        print("\n[Test 01] P11-A2: Sustain惩罚制测试")
        print("-" * 60)
        
        # 测试场景1: Sustain=0（旧逻辑会导致final_score=0，新逻辑不应为0）
        score1, penalty1 = self.engine.apply_sustain_penalty(50.0, 0.0)
        print(f"  场景1 - Sustain=0%: 得分={score1:.1f}, 惩罚={penalty1:.1f}")
        self.assertGreater(score1, 0, "Sustain=0时不应导致final_score=0")
        self.assertEqual(penalty1, 25.0, "Sustain=0应扣25分")
        
        # 测试场景2: Sustain=30（较差）
        score2, penalty2 = self.engine.apply_sustain_penalty(50.0, 30.0)
        print(f"  场景2 - Sustain=30%: 得分={score2:.1f}, 惩罚={penalty2:.1f}")
        self.assertGreater(score2, 0, "Sustain=30%时不应导致final_score=0")
        self.assertEqual(penalty2, 10.0, "Sustain=30应扣10分")
        
        # 测试场景3: Sustain=60（及格，不应扣分）
        score3, penalty3 = self.engine.apply_sustain_penalty(50.0, 60.0)
        print(f"  场景3 - Sustain=60%: 得分={score3:.1f}, 惩罚={penalty3:.1f}")
        self.assertEqual(score3, 50.0, "Sustain=60%时不应扣分")
        self.assertEqual(penalty3, 0.0, "Sustain=60%惩罚应为0")
        
        # 测试场景4: Sustain=90（优秀，应有奖励）
        score4, penalty4 = self.engine.apply_sustain_penalty(50.0, 90.0)
        print(f"  场景4 - Sustain=90%: 得分={score4:.1f}, 惩罚={penalty4:.1f}")
        self.assertGreater(score4, 50.0, "Sustain=90%时应有奖励")
        
        print("✅ P11-A2测试通过: Sustain改为惩罚制，不会导致final_score=0")
    
    def test_02_high_resolution_base_score(self):
        """
        P11-A3: 测试高分辨率基础分（线性极值映射）
        
        验证: 20%量比票的基础分显著高于5%量比票
        """
        print("\n[Test 02] P11-A3: 高分辨率基础分测试")
        print("-" * 60)
        
        max_amount = 1000000  # 100万元作为归一化基准
        
        # 测试场景1: 量比5 vs 量比20（相同涨幅和成交额）
        score_vol5 = self.engine.calculate_base_score_v18(
            volume_ratio=5.0, true_change=10.0, amount=500000, max_amount_in_pool=max_amount
        )
        score_vol20 = self.engine.calculate_base_score_v18(
            volume_ratio=20.0, true_change=10.0, amount=500000, max_amount_in_pool=max_amount
        )
        
        print(f"  量比5.0票: 基础分={score_vol5:.1f}")
        print(f"  量比20.0票: 基础分={score_vol20:.1f}")
        print(f"  分差: {score_vol20 - score_vol5:.1f}分")
        
        self.assertGreater(score_vol20, score_vol5, "量比20的票应得分更高")
        self.assertAlmostEqual(score_vol5, 40.0, delta=5, msg="量比5基础分应在35-45之间")
        self.assertAlmostEqual(score_vol20, 70.0, delta=5, msg="量比20基础分应在65-75之间")
        
        # 测试场景2: 涨幅5% vs 涨幅15%
        score_chg5 = self.engine.calculate_base_score_v18(
            volume_ratio=10.0, true_change=5.0, amount=500000, max_amount_in_pool=max_amount
        )
        score_chg15 = self.engine.calculate_base_score_v18(
            volume_ratio=10.0, true_change=15.0, amount=500000, max_amount_in_pool=max_amount
        )
        
        print(f"\n  涨幅5%票: 基础分={score_chg5:.1f}")
        print(f"  涨幅15%票: 基础分={score_chg15:.1f}")
        print(f"  分差: {score_chg15 - score_chg5:.1f}分")
        
        self.assertGreater(score_chg15, score_chg5, "涨幅15%的票应得分更高")
        
        # 测试场景3: 验证基础分范围
        score_max = self.engine.calculate_base_score_v18(
            volume_ratio=50.0, true_change=30.0, amount=1000000, max_amount_in_pool=max_amount
        )
        print(f"\n  极端值票(量比50/涨幅30%): 基础分={score_max:.1f}")
        self.assertLessEqual(score_max, 100.0, "基础分不应超过100")
        
        print("✅ P11-A3测试通过: 基础分具有高分辨率区分度")
    
    def test_03_vwap_penalty_not_multiplier(self):
        """
        P11-A4: 测试VWAP惩罚扣分制（非乘数）
        
        验证: 价格低于VWAP时扣分，高于VWAP时奖励
        """
        print("\n[Test 03] P11-A4: VWAP惩罚扣分制测试")
        print("-" * 60)
        
        vwap = 100.0
        
        # 测试场景1: 价格远低于VWAP（-10%，应扣较多分）
        score1, penalty1 = self.engine.apply_vwap_penalty(80.0, 90.0, vwap)
        print(f"  场景1 - 价格90(低于VWAP10%): 得分={score1:.1f}, 惩罚={penalty1:.1f}")
        self.assertGreater(penalty1, 0, "价格低于VWAP应扣分")
        self.assertAlmostEqual(penalty1, 10.0, delta=2, msg="低于10%应扣约10分")
        
        # 测试场景2: 价格略低于VWAP（-2%，应扣较少分）
        score2, penalty2 = self.engine.apply_vwap_penalty(80.0, 98.0, vwap)
        print(f"  场景2 - 价格98(低于VWAP2%): 得分={score2:.1f}, 惩罚={penalty2:.1f}")
        self.assertGreater(penalty2, 0, "价格低于VWAP应扣分")
        self.assertLess(penalty2, penalty1, "偏离小应扣更少分")
        
        # 测试场景3: 价格等于VWAP（不扣不奖）
        score3, penalty3 = self.engine.apply_vwap_penalty(80.0, 100.0, vwap)
        print(f"  场景3 - 价格100(等于VWAP): 得分={score3:.1f}, 惩罚={penalty3:.1f}")
        self.assertEqual(penalty3, 0.0, "价格等于VWAP不应扣分")
        
        # 测试场景4: 价格高于VWAP（应有奖励）
        score4, penalty4 = self.engine.apply_vwap_penalty(80.0, 105.0, vwap)
        print(f"  场景4 - 价格105(高于VWAP5%): 得分={score4:.1f}, 惩罚={penalty4:.1f}")
        self.assertGreater(score4, 80.0, "价格高于VWAP应有奖励")
        
        # 测试场景5: 极端偏离（应封顶30分）
        score5, penalty5 = self.engine.apply_vwap_penalty(80.0, 70.0, vwap)
        print(f"  场景5 - 价格70(低于VWAP30%): 得分={score5:.1f}, 惩罚={penalty5:.1f}")
        self.assertLessEqual(penalty5, 30.0, "VWAP惩罚应封顶30分")
        self.assertGreaterEqual(score5, 0.0, "得分不应低于0")
        
        print("✅ P11-A4测试通过: VWAP惩罚制生效，非乘数模式")
    
    def test_04_final_score_never_zero_for_valid_input(self):
        """
        综合测试: 有效输入下final_score永不为0
        
        这是CTO和老板最关注的问题
        """
        print("\n[Test 04] 综合测试: 有效输入下final_score永不为0")
        print("-" * 60)
        
        test_cases = [
            {"name": "正常票(量比10/涨幅5%/Sustain80)", "vol": 10, "chg": 5, "sus": 80, "vwap_ratio": 1.0},
            {"name": "低Sustain票(量比15/涨幅8%/Sustain20)", "vol": 15, "chg": 8, "sus": 20, "vwap_ratio": 1.0},
            {"name": "跌破VWAP票(量比12/涨幅6%/Sustain60/VWAP-5%)", "vol": 12, "chg": 6, "sus": 60, "vwap_ratio": 0.95},
            {"name": "极端票(量比30/涨幅20%/Sustain0/VWAP-10%)", "vol": 30, "chg": 20, "sus": 0, "vwap_ratio": 0.90},
        ]
        
        max_amount = 500000
        
        for case in test_cases:
            # 计算基础分
            base_score = self.engine.calculate_base_score_v18(
                case["vol"], case["chg"], max_amount * 0.5, max_amount
            )
            
            # 涨幅乘数
            multiplier = 1.0 + (case["chg"] / 200)
            
            # 初步得分
            preliminary = base_score * multiplier
            
            # 当前价格（基于VWAP比率）
            vwap = 100.0
            current_price = vwap * case["vwap_ratio"]
            
            # 应用VWAP惩罚
            score_after_vwap, _ = self.engine.apply_vwap_penalty(preliminary, current_price, vwap)
            
            # 应用Sustain惩罚
            final_score, _ = self.engine.apply_sustain_penalty(score_after_vwap, case["sus"])
            
            final_score = min(final_score, 100.0)
            
            print(f"  {case['name']}: 基础分={base_score:.1f} 最终得分={final_score:.1f}")
            
            # 关键断言: final_score不应为0（除非极端情况）
            self.assertGreater(final_score, 0, f"{case['name']}的final_score不应为0")
        
        print("✅ 综合测试通过: 所有有效输入下final_score>0")
    
    def test_05_score_differentiation(self):
        """
        区分度测试: 不同质量的票应有明显分数差异
        """
        print("\n[Test 05] 区分度测试: 优质票vs垃圾票分数差异")
        print("-" * 60)
        
        max_amount = 500000
        
        # 优质票特征: 高量比、高涨幅、价格高于VWAP、Sustain好
        premium_base = self.engine.calculate_base_score_v18(20, 15, max_amount, max_amount)
        premium_multiplier = 1.0 + (15 / 200)
        premium_preliminary = premium_base * premium_multiplier
        premium_score, _ = self.engine.apply_vwap_penalty(premium_preliminary, 105, 100)
        premium_score, _ = self.engine.apply_sustain_penalty(premium_score, 90)
        
        # 垃圾票特征: 低量比、低涨幅、价格低于VWAP、Sustain差
        junk_base = self.engine.calculate_base_score_v18(3, 2, max_amount * 0.1, max_amount)
        junk_multiplier = 1.0 + (2 / 200)
        junk_preliminary = junk_base * junk_multiplier
        junk_score, _ = self.engine.apply_vwap_penalty(junk_preliminary, 95, 100)
        junk_score, _ = self.engine.apply_sustain_penalty(junk_score, 30)
        
        print(f"  优质票(量比20/涨幅15%/高于VWAP/Sustain90): 得分={premium_score:.1f}")
        print(f"  垃圾票(量比3/涨幅2%/低于VWAP/Sustain30): 得分={junk_score:.1f}")
        print(f"  分差: {premium_score - junk_score:.1f}分")
        
        # 优质票应显著高于垃圾票
        self.assertGreater(premium_score, junk_score + 20, "优质票应比垃圾票高至少20分")
        
        print("✅ 区分度测试通过: 评分系统能有效区分优质票和垃圾票")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(V18FixTests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印总结
    print("\n" + "="*80)
    print("V18修复验证测试总结")
    print("="*80)
    print(f"测试运行数: {result.testsRun}")
    print(f"通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 所有测试通过！V18核心死律已修复！")
        print("\n修复验证:")
        print("  ✅ P11-A2: Sustain从乘数改为惩罚制，final_score不再为0")
        print("  ✅ P11-A3: 基础分采用线性极值映射，高量比票得分更高")
        print("  ✅ P11-A4: VWAP采用惩罚扣分制，骗炮票可被识别")
    else:
        print("\n❌ 存在测试失败，请检查修复代码")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
