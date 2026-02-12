"""
概念数据更新脚本

从 AkShare 获取所有概念板块及其成分股，生成本地概念映射字典。
建议每周运行一次，保持概念数据更新。

使用方法：
    python tools/update_concepts.py

Author: iFlow CLI
Version: V10.0
Date: 2026-01-16
"""

import sys
import os
import json
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def get_all_concepts():
    """
    获取所有概念板块及其成分股
    
    Returns:
        dict: {股票代码: [概念1, 概念2, ...]}
    """
    try:
        logger.info("开始获取概念板块数据...")
        
        # 1. 获取所有概念板块
        logger.info("正在获取概念板块列表...")
        concept_boards = ak.stock_board_concept_name_em()
        
        if concept_boards.empty:
            logger.error("获取概念板块列表失败")
            return {}
        
        logger.info(f"✅ 获取到 {len(concept_boards)} 个概念板块")
        
        # 2. 遍历每个概念板块，获取成分股
        concept_map = {}  # {股票代码: [概念1, 概念2, ...]}
        concept_details = {}  # {概念名称: {板块代码, 成分股数量, 更新时间}}
        
        total_boards = len(concept_boards)
        processed = 0
        
        for idx, row in concept_boards.iterrows():
            concept_name = row['板块名称']
            concept_code = row['板块代码']
            
            try:
                # 获取该概念的成分股
                logger.info(f"[{processed+1}/{total_boards}] 正在获取概念: {concept_name}...")
                
                cons_df = ak.stock_board_concept_cons_em(symbol=concept_name)
                
                if not cons_df.empty:
                    # 遍历成分股，添加到概念映射
                    for _, stock_row in cons_df.iterrows():
                        stock_code = stock_row['代码']
                        
                        if stock_code not in concept_map:
                            concept_map[stock_code] = []
                        
                        # 避免重复添加
                        if concept_name not in concept_map[stock_code]:
                            concept_map[stock_code].append(concept_name)
                    
                    # 记录概念详情
                    concept_details[concept_name] = {
                        'code': concept_code,
                        'stock_count': len(cons_df),
                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    logger.info(f"  ✅ {concept_name}: {len(cons_df)} 只股票")
                else:
                    logger.warning(f"  ⚠️  {concept_name}: 无成分股")
                
                processed += 1
                
                # 每处理 10 个概念，休息 1 秒，避免请求过快
                if processed % 10 == 0:
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"  ❌ 获取概念 {concept_name} 失败: {e}")
                processed += 1
                continue
        
        logger.info(f"✅ 概念数据获取完成！共 {len(concept_map)} 只股票，{len(concept_details)} 个概念")
        
        return concept_map, concept_details
        
    except Exception as e:
        logger.error(f"获取概念数据失败: {e}")
        import traceback
        traceback.print_exc()
        return {}, {}


def save_concepts_to_file(concept_map, concept_details, output_dir='data'):
    """
    保存概念数据到文件
    
    Args:
        concept_map: 概念映射字典
        concept_details: 概念详情字典
        output_dir: 输出目录
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存概念映射（股票 -> 概念）
        concept_map_file = os.path.join(output_dir, 'concept_map.json')
        with open(concept_map_file, 'w', encoding='utf-8') as f:
            json.dump(concept_map, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 概念映射已保存: {concept_map_file}")
        
        # 保存概念详情（概念 -> 详情）
        concept_details_file = os.path.join(output_dir, 'concept_details.json')
        with open(concept_details_file, 'w', encoding='utf-8') as f:
            json.dump(concept_details, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 概念详情已保存: {concept_details_file}")
        
        # 生成统计信息
        stats = {
            'total_stocks': len(concept_map),
            'total_concepts': len(concept_details),
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'avg_concepts_per_stock': sum(len(concepts) for concepts in concept_map.values()) / len(concept_map) if concept_map else 0
        }
        
        stats_file = os.path.join(output_dir, 'concept_stats.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 统计信息已保存: {stats_file}")
        logger.info(f"\n📊 统计信息:")
        logger.info(f"   - 股票总数: {stats['total_stocks']}")
        logger.info(f"   - 概念总数: {stats['total_concepts']}")
        logger.info(f"   - 平均每只股票概念数: {stats['avg_concepts_per_stock']:.2f}")
        
    except Exception as e:
        logger.error(f"保存概念数据失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("\n" + "="*60)
    print("概念数据更新脚本")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    # 获取概念数据
    concept_map, concept_details = get_all_concepts()
    
    if concept_map:
        # 保存到文件
        save_concepts_to_file(concept_map, concept_details)
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ 概念数据更新完成！耗时: {elapsed_time:.2f} 秒")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0
    else:
        print("\n❌ 概念数据更新失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())