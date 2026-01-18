"""
V14.4 龙虎榜反制功能测试
"""
import unittest
from logic.signal_generator import SignalGenerator

class TestV14_4_LHB_CounterStrike(unittest.TestCase):
    
    def setUp(self):
        self.sg = SignalGenerator()
        self.ai_score_base = 90.0 # 假设 AI 觉得很不错
        self.capital_normal = 10000000 # 资金正常流入 1000万
        
    def test_lhb_trap_detection(self):
        """测试龙虎榜陷阱：豪华榜 + 高开 > 6%"""
        print("\n--- 测试 V14.4: 龙虎榜陷阱识别 ---")
        result = self.sg.calculate_final_signal(
            stock_code="600000",
            ai_score=self.ai_score_base,
            capital_flow=self.capital_normal,
            trend='UP',
            current_pct_change=7.0,
            yesterday_lhb_net_buy=60000000, # 6000万 (豪华)
            open_pct_change=7.5 # 高开 7.5%
        )
        print(f"场景: 豪华榜净买6000万, 高开7.5% -> 结果: {result['signal']} ({result['reason']})")
        
        # 预期：被识别为陷阱，强制 WAIT，分数极低
        self.assertNotEqual(result['signal'], "BUY")
        self.assertIn("陷阱", result['reason'])
        self.assertLess(result['score'], 50)

    def test_weak_to_strong_opportunity(self):
        """测试弱转强：豪华榜 + 平开 (-2% ~ 3%)"""
        print("\n--- 测试 V14.4: 弱转强机会识别 ---")
        result = self.sg.calculate_final_signal(
            stock_code="000001",
            ai_score=self.ai_score_base,
            capital_flow=self.capital_normal,
            trend='UP',
            current_pct_change=1.5,
            yesterday_lhb_net_buy=80000000, # 8000万 (豪华)
            open_pct_change=0.5 # 平开 0.5%
        )
        print(f"场景: 豪华榜净买8000万, 平开0.5% -> 结果: {result['signal']} ({result['reason']})")
        
        # 预期：识别为弱转强，BUY，分数加成
        self.assertEqual(result['signal'], "BUY")
        self.assertIn("弱转强", result['reason'])
        self.assertGreater(result['score'], self.ai_score_base) # 分数应该比原始高 (x1.3)

    def test_normal_lhb_no_impact(self):
        """测试普通榜单：无影响"""
        print("\n--- 测试 V14.4: 普通榜单无影响 ---")
        result = self.sg.calculate_final_signal(
            stock_code="000002",
            ai_score=self.ai_score_base,
            capital_flow=self.capital_normal,
            trend='UP',
            current_pct_change=3.0,
            yesterday_lhb_net_buy=10000000, # 1000万 (未达豪华线)
            open_pct_change=5.0
        )
        # 预期：正常计算，不触发陷阱也不触发弱转强
        self.assertEqual(result['signal'], "BUY")
        self.assertNotIn("陷阱", result['reason'])
        self.assertNotIn("弱转强", result['reason'])

if __name__ == '__main__':
    unittest.main()