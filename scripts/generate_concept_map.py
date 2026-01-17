"""
概念映射生成器

从 AkShare 获取真实的概念数据，生成 concept_map.json
每个股票代码对应一个概念列表
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
import pandas as pd
from logic.logger import get_logger

logger = get_logger(__name__)


def generate_concept_map():
    """
    生成概念映射表

    从 AkShare 获取所有概念板块，然后获取每个板块的成分股，
    构建 股票代码 -> 概念列表 的映射关系
    """
    try:
        import akshare as ak
    except ImportError:
        logger.error("AkShare 未安装，无法生成概念映射")
        return False

    logger.info("开始生成概念映射表...")
    start_time = datetime.now()

    # 1. 获取所有概念板块
    try:
        concept_df = ak.stock_board_concept_name_em()
        logger.info(f"获取到 {len(concept_df)} 个概念板块")

        # 🆕 只获取前 100 个热门概念板块（按涨跌幅排序）
        if not concept_df.empty and '涨跌幅' in concept_df.columns:
            concept_df = concept_df.nlargest(100, '涨跌幅')
            logger.info(f"筛选出前 100 个热门概念板块")
    except Exception as e:
        logger.error(f"获取概念板块失败: {e}")
        return False

    if concept_df.empty:
        logger.error("概念板块数据为空")
        return False

    # 2. 构建股票代码 -> 概念列表的映射
    concept_map = {}
    exclude_concepts = ['融资融券', '深股通', '标准普尔', 'MSCI', '富时罗素', '标普道琼斯', '沪股通']

    total_boards = len(concept_df)
    processed = 0

    for idx, row in concept_df.iterrows():
        board_name = row['板块名称']
        board_code = row['板块代码']

        # 跳过一些太宽泛的概念
        if any(exclude in board_name for exclude in exclude_concepts):
            continue

        processed += 1
        if processed % 50 == 0:
            logger.info(f"已处理 {processed}/{total_boards} 个板块...")

        try:
            # 获取该板块的成分股
            stocks_df = ak.stock_board_concept_cons_em(symbol=board_name)

            if not stocks_df.empty:
                for _, stock_row in stocks_df.iterrows():
                    stock_code = stock_row.get('代码', '')

                    if stock_code:
                        # 清理股票代码（去掉 sh/sz 前缀）
                        if stock_code.startswith('sh') or stock_code.startswith('sz'):
                            stock_code = stock_code[2:]

                        # 添加到映射表
                        if stock_code not in concept_map:
                            concept_map[stock_code] = []

                        # 避免重复添加
                        if board_name not in concept_map[stock_code]:
                            concept_map[stock_code].append(board_name)

        except Exception as e:
            logger.warning(f"获取板块 {board_name} 的成分股失败: {e}")
            continue

    # 3. 保存到文件
    output_path = "data/concept_map.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(concept_map, f, ensure_ascii=False, indent=2)

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"✅ 概念映射表生成完成！")
    logger.info(f"   处理板块数: {processed}")
    logger.info(f"   覆盖股票数: {len(concept_map)}")
    logger.info(f"   耗时: {elapsed:.2f} 秒")
    logger.info(f"   保存路径: {output_path}")

    return True


def test_concept_map():
    """测试概念映射表"""
    import json

    concept_map_path = "data/concept_map.json"

    if not os.path.exists(concept_map_path):
        print("❌ 概念映射表不存在，请先运行 generate_concept_map()")
        return False

    with open(concept_map_path, 'r', encoding='utf-8') as f:
        concept_map = json.load(f)

    print("=" * 60)
    print("概念映射表测试")
    print("=" * 60)
    print(f"覆盖股票数: {len(concept_map)}")

    # 测试几个知名股票
    test_stocks = ['300750', '000858', '002594', '688981', '300015']

    print("\n测试股票概念:")
    for code in test_stocks:
        if code in concept_map:
            concepts = concept_map[code]
            print(f"  {code}: {concepts[:3]}")  # 只显示前3个概念
        else:
            print(f"  {code}: 无概念数据")

    print("=" * 60)
    return True


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_concept_map()
    else:
        success = generate_concept_map()
        if success:
            print("\n🎉 概念映射表生成成功！")
            print("运行 'python scripts/generate_concept_map.py test' 来测试")
        else:
            print("\n❌ 概念映射表生成失败！")
            sys.exit(1)