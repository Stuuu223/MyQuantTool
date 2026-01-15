"""
测试龙头战法数据展示
"""
import sys
sys.path.append('E:\\MyQuantTool')

from logic.algo import QuantAlgo

print("=" * 60)
print("测试龙头战法数据展示")
print("=" * 60)

# 扫描参数
limit = 20
min_score = 40

print(f"\n扫描参数：")
print(f"  - 扫描数量限制: {limit}")
print(f"  - 最低评分门槛: {min_score}")

# 执行扫描
print(f"\n开始扫描...")
result = QuantAlgo.scan_dragon_stocks(limit=limit, min_score=min_score)

# 显示结果
print(f"\n扫描结果：")
print(f"  - 数据状态: {result['数据状态']}")

if result['数据状态'] == '正常':
    print(f"  - 扫描数量: {result['扫描数量']}")
    print(f"  - 涨停板数量: {result['涨停板数量']}")
    print(f"  - 分析数量: {result['分析数量']}")
    print(f"  - 符合条件数量: {result['符合条件数量']}")

    if result['符合条件数量'] > 0:
        print(f"\n符合龙头战法条件的股票：")
        for i, stock in enumerate(result['龙头股列表'][:10], 1):
            print(f"\n{i}. {stock['龙头评级']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评级得分']}")
            print(f"   最新价: ¥{stock['最新价']:.2f}")
            print(f"   涨跌幅: {stock['涨跌幅']:.2f}%")
            print(f"   量比: {stock.get('量比', 0):.2f}")
            print(f"   换手率: {stock.get('换手率', 0):.2f}%")
            print(f"   竞价量: {stock.get('竞价量', 0)} 手")
            print(f"   评级说明: {stock['评级说明']}")
    else:
        print(f"\n❌ 未找到符合龙头战法条件的股票")
else:
    print(f"  - 错误信息: {result.get('错误信息', '')}")
    print(f"  - 说明: {result.get('说明', '')}")

print("\n" + "=" * 60)