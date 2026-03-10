# tools/test_touyan_token.py
# 投研版Token接口 MVP验证脚本
# 目标：验证 xtdatacenter 能否通过 Token 突破券商版 tick 深度限制
# 运行：E:\MyQuantTool\venv_qmt\Scripts\python.exe tools/test_touyan_token.py
# 预期：成功拉取 >1个月前的 tick 数据，则投研版接口可用

import os
import sys
import time

print("=" * 60)
print("投研版Token接口 MVP 验证")
print("=" * 60)

# ============================================================
# Step 0: 读取环境变量
# ============================================================
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 没有 dotenv 就靠系统环境变量

TOKEN = os.getenv("QMT_VIP_TOKEN", "")
QMT_PATH = os.getenv("QMT_PATH", r"E:\qmt\userdata_mini")

if not TOKEN:
    print("[FATAL] QMT_VIP_TOKEN 未设置，请检查 .env 文件")
    sys.exit(1)

print(f"[OK]   Token: {TOKEN[:8]}...{TOKEN[-4:]}")
print(f"[OK]   数据目录: {QMT_PATH}")

# ============================================================
# Step 1: 检查 xtquant 版本是否支持 xtdatacenter
# ============================================================
try:
    import xtquant
    ver = getattr(xtquant, '__version__', 'unknown')
    print(f"[OK]   xtquant 版本: {ver}")
except ImportError:
    print("[FATAL] xtquant 未安装，请运行: pip install xtquant")
    sys.exit(1)

try:
    from xtquant import xtdatacenter as xtdc
    print("[OK]   xtdatacenter 模块加载成功")
except ImportError:
    print("[FATAL] xtdatacenter 模块不存在，版本过旧")
    print("        请运行: pip install xtquant --upgrade")
    sys.exit(1)

from xtquant import xtdata

# ============================================================
# Step 2: 激活投研版 Token 通道
# ============================================================
print("\n[...] 正在连接投研版数据服务器（约10-30秒）...")

try:
    xtdc.set_data_home_dir(QMT_PATH)  # 数据落盘到 miniQMT 同一目录
    xtdc.set_token(TOKEN)
    xtdc.init(False)                  # False = 不阻塞主线程
    port = xtdc.listen(port=(58620, 58650))
    xtdata.connect(port=port)
    print(f"[OK]   投研版通道建立，监听端口: {port}")
    print(f"[OK]   数据实际目录: {xtdata.data_dir}")
except Exception as e:
    print(f"[FAIL] 连接失败: {e}")
    print("       可能原因: Token过期 / 网络问题 / xtquant版本过旧")
    sys.exit(1)

# ============================================================
# Step 3: 核心验证 - 下载1年前的 tick 数据
# 选 000001.SZ 平安银行，每天成交量大，数据必然存在
# 如果能下到去年的 tick，则证明投研版接口完全可用
# ============================================================
TEST_STOCK = "000001.SZ"
TICK_TEST_DATE = "20250101"  # 距今约14个月，远超券商版1个月上限

print(f"\n[...] 核心测试：下载 {TEST_STOCK} 在 {TICK_TEST_DATE} 的 tick 数据...")
print(f"      （若成功，证明投研版接口突破了券商版1个月限制）")

t0 = time.time()
try:
    xtdata.download_history_data2(
        stock_list=[TEST_STOCK],
        period="tick",
        start_time=TICK_TEST_DATE,
        end_time="20250108",  # 只取一周，够验证就行
        callback=lambda info: print(f"        进度: {info}") if info else None
    )
    elapsed = time.time() - t0
    print(f"[OK]   download_history_data2 完成，耗时 {elapsed:.1f}s")
except Exception as e:
    print(f"[FAIL] 下载调用失败: {e}")
    sys.exit(1)

# ============================================================
# Step 4: 读取本地数据，验证真实落盘
# ============================================================
print(f"\n[...] 读取本地已落盘数据验证...")
try:
    tick_df = xtdata.get_local_data(
        field_list=["time", "lastPrice", "volume", "amount"],
        stock_list=[TEST_STOCK],
        period="tick",
        start_time=TICK_TEST_DATE,
        end_time="20250108"
    )
except Exception as e:
    print(f"[FAIL] get_local_data 调用失败: {e}")
    sys.exit(1)

if TEST_STOCK in tick_df and tick_df[TEST_STOCK] is not None:
    df = tick_df[TEST_STOCK]
    if hasattr(df, '__len__') and len(df) > 0:
        print(f"\n{'='*60}")
        print(f"✅  验证通过！")
        print(f"    股票: {TEST_STOCK}")
        print(f"    日期: {TICK_TEST_DATE} 起")
        print(f"    Tick 条数: {len(df)}")
        print(f"    投研版 Token 接口完全可用！")
        print(f"    可以突破券商版1个月限制，拉取约1年历史tick")
        print(f"{'='*60}")
        # 打印前几条数据验证真实性
        try:
            import pandas as pd
            if isinstance(df, pd.DataFrame):
                print("\n[数据预览 - 前3条]:")
                print(df.head(3).to_string())
        except Exception:
            pass
    else:
        print(f"\n❌  验证失败：数据返回为空")
        print(f"    可能原因: Token权限不包含tick历史 / 该日期无数据")
else:
    print(f"\n❌  验证失败：{TEST_STOCK} 不在返回数据中")
    print(f"    Token 可能未生效，仍在走券商版通道")

# ============================================================
# Step 5: 附加验证 - 测试1m数据深度（3年）
# ============================================================
print(f"\n[...] 附加验证：1m数据深度测试（投研版应支持3年）...")
try:
    xtdata.download_history_data2(
        stock_list=[TEST_STOCK],
        period="1m",
        start_time="20230101",
        end_time="20230110"
    )
    df_1m = xtdata.get_local_data(
        field_list=["time", "close", "volume"],
        stock_list=[TEST_STOCK],
        period="1m",
        start_time="20230101",
        end_time="20230110"
    )
    if TEST_STOCK in df_1m and df_1m[TEST_STOCK] is not None:
        df = df_1m[TEST_STOCK]
        if hasattr(df, '__len__') and len(df) > 0:
            print(f"✅  1m数据验证通过：2023年数据 {len(df)} 条")
        else:
            print(f"❌  1m数据为空（券商版通常也支持1年，若空则有问题）")
except Exception as e:
    print(f"[WARN] 1m数据验证异常: {e}")

print("\n[完成] MVP验证结束")
