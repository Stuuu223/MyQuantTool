# -*- coding: utf-8 -*-
"""
投研版 Token 隔离验证实验
核心原则：下载前=0，下载后>0，才算 Token 真正有效

测试日期选 2024-10-08（节后第一天，交易量大，数据必然存在于云端）
该日期远在你 MiniQMT 开始运行之前，本地绝对没有

运行方法:
  E:\MyQuantTool\venv_qmt\Scripts\python.exe tools/verify_vip_token_isolation.py
  # 或指定股票:
  E:\MyQuantTool\venv_qmt\Scripts\python.exe tools/verify_vip_token_isolation.py --stock 301368.SZ
"""

import os, sys, time, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── 测试窗口：必须在你 MiniQMT 开始运行之前 ──────────────────
TEST_DATE_START = "20241008"  # 2024国庆节后第一天，交易量极大
TEST_DATE_END = "20241010"  # 三天足够验证

# ── 候选冷门股：脚本自动找本地为空的那只 ────────────────────
COLD_CANDIDATES = [
    "301368.SZ",  # 北交所
    "833171.BJ",  # 北交所
    "430489.BJ",  # 北交所
    "831832.BJ",  # 北交所
    "688798.SH",  # 科创板冷门
    "001215.SZ",  # 主板小盘
    "603321.SH",  # 主板小盘
]


def log(msg, level="INFO"):
    icons = {"OK": "✅", "FAIL": "❌", "WARN": "⚠️ ", "STEP": ">>>"}
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] {icons.get(level,'')} {msg}",
        flush=True,
    )


def count_local_ticks(xtdata, stock):
    """读本地 Tick 条数，不触网"""
    try:
        raw = xtdata.get_local_data(
            field_list=[],
            stock_list=[stock],
            period="tick",
            start_time=TEST_DATE_START,
            end_time=TEST_DATE_END,
            count=-1,
        )
        df = raw.get(stock)
        return 0 if df is None else len(df)
    except Exception:
        return 0


def find_cold_stock(xtdata):
    log("寻找本地磁盘为空的冷门标的...", "STEP")
    for s in COLD_CANDIDATES:
        n = count_local_ticks(xtdata, s)
        if n == 0:
            log(f"{s} 本地={n} 条 ← 选定", "OK")
            return s
        log(f"{s} 本地已有 {n} 条，跳过", "WARN")
    return None


def activate_vip(token, qmt_dir):
    from xtquant import xtdatacenter as xtdc, xtdata

    log("激活投研版 Token 通道...", "STEP")
    xtdc.set_data_home_dir(qmt_dir)
    xtdc.set_token(token)
    xtdc.init(False)
    port = xtdc.listen(port=(58620, 58650))
    xtdata.connect(port=port)
    log(f"通道建立，端口 {port}，落盘目录: {xtdata.data_dir}", "OK")
    return xtdata


def run_experiment(xtdata, stock):
    before = count_local_ticks(xtdata, stock)
    log(f"[下载前] 本地 Tick = {before} 条")

    if before > 0:
        return {
            "verdict": "INVALID",
            "before": before,
            "after": before,
            "msg": "实验无效：本地已有数据，无法隔离",
        }

    # 下载指令
    log(f"发送下载指令 → {stock} {TEST_DATE_START}~{TEST_DATE_END}", "STEP")
    t0 = time.time()
    try:
        xtdata.download_history_data2(
            stock_list=[stock],
            period="tick",
            start_time=TEST_DATE_START,
            end_time=TEST_DATE_END,
            callback=None,
        )
    except AttributeError:
        # 旧版没有 data2，退回普通接口
        log("download_history_data2 不存在，退回 download_history_data", "WARN")
        xtdata.download_history_data(
            stock_code=stock,
            period="tick",
            start_time=TEST_DATE_START,
            end_time=TEST_DATE_END,
        )
    except Exception as e:
        return {"verdict": "DOWNLOAD_FAILED", "before": 0, "after": 0, "msg": str(e)}

    # 轮询落盘（最多 180 秒）
    log("等待落盘，每 15 秒探测一次（最多 3 分钟）...")
    after, waited = 0, 0
    while waited < 180:
        time.sleep(15)
        waited += 15
        after = count_local_ticks(xtdata, stock)
        log(f"  [{waited}s] 本地 Tick = {after} 条")
        if after > 0:
            break

    elapsed = round(time.time() - t0, 1)
    if after > 0:
        return {
            "verdict": "PASS",
            "before": 0,
            "after": after,
            "elapsed_s": elapsed,
            "msg": f"Token 有效，从云端拉取了 {after} 条 Tick（耗时 {elapsed}s）",
        }
    else:
        return {
            "verdict": "FAIL",
            "before": 0,
            "after": 0,
            "elapsed_s": elapsed,
            "msg": (
                "Token 无效或权限不足。等待 180s 后本地仍为 0 条。\n"
                "  可能原因:\n"
                "  1. Token 未激活 / 已过期\n"
                "  2. 迅投数据中心无该股票该日期的 Tick\n"
                "  3. xtdatacenter 版本过旧\n"
                "  4. 网络问题导致云端未传输"
            ),
        }


def print_report(cfg, stock, result):
    sep = "=" * 68
    print(f"\n{sep}")
    print("  投研版 Token 隔离验证实验报告")
    print(sep)
    print(f"  运行时间 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  测试标的 : {stock}")
    print(f"  测试日期 : {TEST_DATE_START} ~ {TEST_DATE_END}")
    print(f"  下载前   : {result['before']} 条")
    print(f"  下载后   : {result['after']} 条")
    print(sep)

    v = result["verdict"]
    if v == "PASS":
        print(f"  判决: ✅  PASS")
        print(f"\n  ✅ Token 真正有效。可以突破本地缓存，从云端拉取历史 Tick。")
        print("  ✅ 扩库计划（batch_download_samples.py）可以继续推进。")
        print("  ✅ 建议将 Token 激活逻辑集成到 smart_download.py 主流程。")
    elif v == "FAIL":
        print(f"  判决: ❌  FAIL")
        print(f"\n{result['msg']}")
        print()
        print("  ❌ 结论：当前 Token 无法突破本地缓存。")
        print("     回测样本天花板 = MiniQMT 订阅窗口内的数据（约 2-3 个月）。")
        print("     所有基于投研版可拉1年历史Tick的架构决策必须暂停。")
        print("     建议：联系迅投确认 Token 权限等级，或采购正式投研版授权。")
    elif v == "INVALID":
        print(f"  判决: ⚠️  INVALID — 实验无效，本地已有数据")
        print("  请换一只本地磁盘绝对没有的股票重试：")
        print("  python tools/verify_vip_token_isolation.py --stock 831832.BJ")
    else:
        print(f"  判决: ❌  {v} — {result['msg']}")

    print(sep)

    # 保存 JSON
    try:
        out = Path(__file__).parent.parent / "data" / "validation"
        out.mkdir(parents=True, exist_ok=True)
        fname = (
            out / f"vip_token_isolation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "stock": stock,
                    "result": result,
                    "run_at": datetime.now().isoformat(),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"  报告已保存: {fname}")
    except Exception:
        pass


def main():
    print("=" * 68)
    print("  投研版 Token 隔离验证实验")
    print("  判定标准：下载前=0 → 下载后>0，才算有效")
    print("=" * 68)

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    token = os.getenv("QMT_VIP_TOKEN", "")
    qmt_dir = os.getenv("QMT_PATH", r"E:\qmt\userdata_mini")

    # --stock 参数
    stock_arg = None
    for i, a in enumerate(sys.argv[1:], 1):
        if a.startswith("--stock="):
            stock_arg = a.split("=", 1)[1]
        elif a == "--stock" and i < len(sys.argv):
            stock_arg = sys.argv[i + 1]

    if not token:
        log("QMT_VIP_TOKEN 未设置，请检查 .env 文件", "FAIL")
        sys.exit(1)

    try:
        xtdata = activate_vip(token, qmt_dir)
    except Exception as e:
        log(f"投研版通道激活失败: {e}", "FAIL")
        sys.exit(1)

    if stock_arg:
        n = count_local_ticks(xtdata, stock_arg)
        if n > 0:
            log(f"⚠️ {stock_arg} 本地已有 {n} 条，实验可能被污染", "WARN")
        test_stock = stock_arg
    else:
        test_stock = find_cold_stock(xtdata)
        if not test_stock:
            log("所有候选股本地均有数据，无法自动选定", "FAIL")
            log("请用 --stock 手动指定一只本地绝对没有的股票")
            sys.exit(1)

    result = run_experiment(xtdata, test_stock)
    print_report({"token": token, "qmt_dir": qmt_dir}, test_stock, result)
    sys.exit(0 if result["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
