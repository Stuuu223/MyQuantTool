# -*- coding: utf-8 -*-
"""
下载2026-01-05的Tick数据
用于跨日回演支持

Author: AI Data Engineer
Date: 2026-02-23
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from logic.data_providers.qmt_manager import QmtDataManager
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def download_0105_data():
    """
    下载2026-01-05的Tick数据
    
    Returns:
        dict: 下载报告
    """
    print("=" * 70)
    print("【下载2026-01-05 Tick数据】")
    print("=" * 70)
    
    # 初始化管理器
    manager = QmtDataManager()
    
    # 启动VIP服务
    logger.info("启动VIP行情服务...")
    port_info = manager.start_vip_service()
    if port_info:
        logger.info(f"VIP服务已启动，监听端口: {port_info[1]}")
    else:
        logger.warning("VIP服务启动失败，将使用普通下载")
    
    # 读取66只股票列表
    csv_path = project_root / 'data' / 'cleaned_candidates_66.csv'
    logger.info(f"读取股票列表: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path)
        stock_list = df['ts_code'].tolist()
        logger.info(f"成功读取 {len(stock_list)} 只股票")
    except Exception as e:
        logger.error(f"读取股票列表失败: {e}")
        return {"error": str(e)}
    
    # 显示前10只股票
    print(f"\n股票列表预览 (前10只):")
    for i, code in enumerate(stock_list[:10], 1):
        print(f"  {i}. {code}")
    print(f"  ... 共 {len(stock_list)} 只")
    
    trade_date = '20260105'
    
    # 批量下载Tick数据
    logger.info(f"\n开始下载 {trade_date} 的Tick数据...")
    print(f"\n【批量下载Tick数据】日期: {trade_date} | 股票数: {len(stock_list)}")
    
    tick_results = manager.download_tick_data(
        stock_list=stock_list,
        trade_date=trade_date,
        use_vip=True,
        check_existing=True,
        delay=0.2
    )
    
    # 统计下载结果
    success_count = sum(1 for r in tick_results.values() if r.success)
    failed_count = len(tick_results) - success_count
    total_records = sum(r.record_count for r in tick_results.values())
    
    print(f"\n初步下载完成:")
    print(f"  成功: {success_count}/{len(stock_list)}")
    print(f"  失败: {failed_count}/{len(stock_list)}")
    print(f"  总记录数: {total_records}")
    
    # 验证数据完整性
    logger.info("\n验证数据完整性...")
    print(f"\n【数据完整性验证】")
    
    reports = manager.verify_data_integrity(
        stock_list=stock_list,
        trade_date=trade_date,
        check_periods=['tick']
    )
    
    # 找出缺失的股票
    missing_stocks = [
        code for code, report in reports.items() 
        if not report.has_tick
    ]
    
    complete_count = len(stock_list) - len(missing_stocks)
    print(f"  完整: {complete_count}/{len(stock_list)}")
    print(f"  缺失: {len(missing_stocks)}/{len(stock_list)}")
    
    # 补充下载缺失的数据
    if missing_stocks:
        logger.info(f"\n补充下载 {len(missing_stocks)} 只缺失的股票...")
        print(f"\n【补充下载缺失数据】{len(missing_stocks)} 只股票")
        
        # 构建缺失列表 [(stock_code, period), ...]
        missing_list = [(code, 'tick') for code in missing_stocks]
        
        supplement_results = manager.supplement_missing_data(
            missing_list=missing_list,
            use_vip=True
        )
        
        # 再次验证
        logger.info("再次验证数据完整性...")
        reports = manager.verify_data_integrity(
            stock_list=stock_list,
            trade_date=trade_date,
            check_periods=['tick']
        )
        
        final_missing = [
            code for code, report in reports.items() 
            if not report.has_tick
        ]
        
        print(f"\n补充下载后:")
        print(f"  完整: {len(stock_list) - len(final_missing)}/{len(stock_list)}")
        print(f"  仍缺失: {len(final_missing)}/{len(stock_list)}")
        
        if final_missing:
            print(f"\n仍缺失的股票:")
            for code in final_missing[:10]:
                print(f"  - {code}")
            if len(final_missing) > 10:
                print(f"  ... 等共 {len(final_missing)} 只")
    else:
        final_missing = []
    
    # 生成下载报告
    final_complete = len(stock_list) - len(final_missing)
    completeness_rate = final_complete / len(stock_list) * 100
    
    report_data = {
        "report_title": "2026-01-05 Tick数据下载报告",
        "generated_at": datetime.now().isoformat(),
        "trade_date": trade_date,
        "total_stocks": len(stock_list),
        "download_summary": {
            "initial_success": success_count,
            "initial_failed": failed_count,
            "total_records": total_records,
            "final_complete": final_complete,
            "final_missing": len(final_missing),
            "completeness_rate": f"{completeness_rate:.2f}%"
        },
        "missing_stocks": final_missing,
        "stock_details": {
            code: {
                "has_tick": report.has_tick,
                "tick_count": report.tick_count,
                "missing_periods": report.missing_periods
            }
            for code, report in reports.items()
        }
    }
    
    # 保存报告
    report_path = project_root / 'data' / 'download_0105_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n【报告已生成】")
    print(f"  路径: {report_path}")
    print(f"  完整度: {completeness_rate:.2f}%")
    
    print("\n" + "=" * 70)
    print("【下载任务完成】")
    print("=" * 70)
    
    return report_data


if __name__ == "__main__":
    try:
        result = download_0105_data()
        
        # 打印最终摘要
        if "error" not in result:
            summary = result.get("download_summary", {})
            print(f"\n📊 最终摘要:")
            print(f"  目标日期: 2026-01-05")
            print(f"  目标股票: {result.get('total_stocks', 0)} 只")
            print(f"  下载成功: {summary.get('final_complete', 0)} 只")
            print(f"  数据缺失: {summary.get('final_missing', 0)} 只")
            print(f"  完整度: {summary.get('completeness_rate', 'N/A')}")
            
            if summary.get('final_missing', 0) == 0:
                print(f"\n✅ 所有股票数据下载完成！")
            else:
                print(f"\n⚠️  部分股票数据缺失，请查看报告了解详情")
        else:
            print(f"\n❌ 下载失败: {result['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断下载")
        sys.exit(130)
    except Exception as e:
        logger.error(f"下载过程发生错误: {e}", exc_info=True)
        print(f"\n❌ 下载失败: {e}")
        sys.exit(1)
