#!/usr/bin/env python3
"""
测试QMT连接
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_qmt():
    """测试QMT连接"""
    print("=" * 80)
    print("🔧 测试QMT连接")
    print("=" * 80)

    try:
        print("\n1️⃣ 导入xtquant模块...")
        from xtquant import xtdatacenter as xtdc
        from xtquant import xtdata
        print("   ✅ 导入成功")

        print("\n2️⃣ 设置数据目录...")
        data_dir = PROJECT_ROOT / 'data' / 'qmt_data'
        data_dir.mkdir(parents=True, exist_ok=True)
        xtdc.set_data_home_dir(str(data_dir))
        print(f"   ✅ 数据目录: {data_dir}")

        print("\n3️⃣ 设置Token...")
        VIP_TOKEN = "6b1446e317ed67596f13d2e808291a01e0dd9839"
        xtdc.set_token(VIP_TOKEN)
        print(f"   ✅ Token: {VIP_TOKEN[:6]}...{VIP_TOKEN[-4:]}")

        print("\n4️⃣ 初始化服务...")
        xtdc.init()
        print("   ✅ 初始化成功")

        print("\n5️⃣ 启动监听...")
        listen_port = xtdc.listen(port=(58700, 58720))
        print(f"   ✅ 监听端口: {listen_port}")

        print("\n6️⃣ 连接行情服务...")
        _, port = listen_port
        xtdata.connect(ip='127.0.0.1', port=port, remember_if_success=False)
        print("   ✅ 连接请求已发送")

        print("\n7️⃣ 等待连接成功...")
        import time
        for i in range(10):
            try:
                result = xtdata.get_market_data(['close'], ['600519.SH'], count=1)
                if result is not None:
                    print("   ✅ 连接成功！")
                    print(f"   测试数据: {result}")
                    break
            except Exception as e:
                pass
            print(f"   等待中... {i+1}/10")
            time.sleep(1)
        else:
            print("   ❌ 连接超时")

        print("\n8️⃣ 测试下载单个股票...")
        test_code = "000001.SZ"
        print(f"   测试股票: {test_code}")
        try:
            xtdata.download_history_data(
                stock_code=test_code,
                period='tick',
                start_time='20251121000000'
            )
            print("   ✅ 下载成功！")
        except Exception as e:
            print(f"   ❌ 下载失败: {e}")

        print("\n" + "=" * 80)
        print("🎉 测试完成！")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_qmt()