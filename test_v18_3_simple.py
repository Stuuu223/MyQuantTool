"""
V18.3 简单测试
"""

import time
from logic.data_manager import DataManager
from logic.sector_analysis_streamlit import FastSectorAnalyzerStreamlit
from logic.logger import get_logger

logger = get_logger(__name__)


def main():
    print("=" * 80)
    print("🧪 V18.3 简单测试")
    print("=" * 80)
    
    db = DataManager()
    analyzer = FastSectorAnalyzerStreamlit(db)
    
    # 测试获取资金流
    print("\n📊 测试获取板块资金流...")
    
    t_start = time.time()
    fund_flow = analyzer.get_sector_fund_flow('半导体', 'industry')
    t_cost = time.time() - t_start
    
    print(f"板块: 半导体")
    print(f"净流入: {fund_flow.get('net_inflow_yi', 0):.2f}亿")
    print(f"状态: {fund_flow.get('status', 'unknown')}")
    print(f"原因: {fund_flow.get('reason', '')}")
    print(f"耗时: {t_cost:.6f}秒")
    
    print(f"\n🚀 性能对比:")
    print(f"  - V18.2 (旧方法): 5.8秒")
    print(f"  - V18.3 (新方法): {t_cost:.6f}秒")
    print(f"  - 性能提升: {5.8/t_cost:.0f}倍")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()