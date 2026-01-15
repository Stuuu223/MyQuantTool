# -*- coding: utf-8 -*-
"""测试数据源管理器"""
from logic.data_manager import DataManager
from logic.data_source_manager import DataSourceManager

def test_datasource():
    print("=" * 60)
    print("测试数据源管理器")
    print("=" * 60)

    # 初始化
    db = DataManager()
    data_source_manager = DataSourceManager(db)

    # 测试获取一只股票的数据
    code = "600519"
    start_date = "20240101"
    end_date = "20241231"

    print(f"\n获取股票数据: {code}")
    print(f"日期范围: {start_date} - {end_date}")

    df = data_source_manager.get_stock_data(code, start_date, end_date)

    if df is not None:
        print(f"\n成功获取数据:")
        print(f"  行数: {len(df)}")
        print(f"  列名: {list(df.columns)}")
        print(f"  索引类型: {type(df.index)}")
        print(f"  前5行:")
        print(df.head())
        print(f"\n  后5行:")
        print(df.tail())
    else:
        print(f"\n获取数据失败")

if __name__ == "__main__":
    test_datasource()