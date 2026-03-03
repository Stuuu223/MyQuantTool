"""
智能下载器 - 日K本地读取 + Tick精准狙击
用法:
    python tools/smart_download.py                           # 默认上个交易日
    python tools/smart_download.py 20260303                  # 单日
    python tools/smart_download.py 20260206 20260303         # 日期范围(逐日粗筛)
    python tools/smart_download.py 20260206 20260303 --full  # 日期范围(全量补Tick,跳过粗筛)
设计原则:
  1. 日K直接读本地，不调用download
  2. 常规模式：逐日粗筛后下载Tick
  3. --full模式：全市场直准补1次，导出 tick_index内索引
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


def get_trading_days(start_date: str, end_date: str, xtdata) -> list[str]:
    """ETF日K判断交易日，完全不依赖交易日历接口"""
    try:
        raw = xtdata.get_local_data(
            field_list=['close'],
            stock_list=['510300.SH'],
            period='1d',
            start_time=start_date,
            end_time=end_date
        )
        df = raw.get('510300.SH')
        if df is not None and not df.empty:
            return [str(idx)[:8] if len(str(idx)) > 8 else str(idx)
                    for idx in df.index.tolist()]
    except Exception:
        pass
    # 兑底：排除周末
    from datetime import timedelta
    s = datetime.strptime(start_date, '%Y%m%d')
    e = datetime.strptime(end_date,   '%Y%m%d')
    days = []
    cur = s
    while cur <= e:
        if cur.weekday() < 5:
            days.append(cur.strftime('%Y%m%d'))
        cur += timedelta(days=1)
    return days


def download_one_day(date: str, stocks: list, xtdata, full: bool):
    """\u5bf9单个交易日发送Tick下载指令"""
    try:
        xtdata.download_history_data2(
            stock_list=stocks,
            period='tick',
            start_time=date,
            end_time=date,
        )
    except Exception as e:
        print(f"  ❗ download_history_data2异常: {e}，切换单只备用...")
        for i, s in enumerate(stocks):
            try:
                xtdata.download_history_data(s, 'tick',
                                             start_time=date, end_time=date)
            except Exception:
                pass
            if (i + 1) % 100 == 0:
                print(f"  ...{i+1}/{len(stocks)}...")

    # 更新 tick_index
    try:
        idx_dir = Path(__file__).parent.parent / 'data' / 'tick_index'
        idx_dir.mkdir(parents=True, exist_ok=True)
        with open(idx_dir / f'{date}.json', 'w', encoding='utf-8') as f:
            json.dump({
                'date': date,
                'mode': 'full' if full else 'filtered',
                'count': len(stocks),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def main():
    from xtquant import xtdata
    from logic.core.config_manager import get_config_manager
    from logic.utils.calendar_utils import get_latest_completed_trading_day

    cfg  = get_config_manager()
    args = sys.argv[1:]
    full_mode = '--full' in args
    dates_args = [a for a in args if not a.startswith('--')]

    if len(dates_args) >= 2:
        start_date, end_date = dates_args[0], dates_args[1]
    elif len(dates_args) == 1:
        start_date = end_date = dates_args[0]
    else:
        start_date = end_date = get_latest_completed_trading_day()

    print('=' * 52)
    mode_label = 'FULL全量' if full_mode else '粗筛'
    print(f'🚀 智能下载器 | {start_date}~{end_date} | {mode_label}')
    print('=' * 52)

    port = cfg.get('system_and_risk.qmt_port', 58610)
    print(f'🔌 连接端口 {port}...')
    try:
        xtdata.connect(port=port)
        print('✅ 连接成功')
    except Exception as e:
        print(f'❌ 连接失败: {e}')
        return

    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    print(f'🔍 全市场 {len(all_stocks)} 只股票')

    # ── 阶段一：检查本地日K（不主动download）──
    print('\n[阶段一] 检查本地日K...')
    sample_data = xtdata.get_local_data(
        field_list=['close'], stock_list=all_stocks[:10],
        period='1d', start_time=end_date, end_time=end_date
    )
    valid_n = sum(1 for s in all_stocks[:10]
                  if s in sample_data and sample_data[s] is not None
                  and len(sample_data[s]) > 0)
    if valid_n >= 5:
        print(f'  ✅ 本地日K充足 ({valid_n}/10)，跳过下载')
    else:
        print(f'  ⚠️ 本地日K不足 ({valid_n}/10)，请先在QMT客户端手动下载日K再运行本脚本')
        return

    # 获取交易日列表
    trading_days = get_trading_days(start_date, end_date, xtdata)
    print(f'  📅 交易日: {trading_days}')

    if full_mode:
        # ── FULL模式：逐日全市场一次打包 ──
        print(f'\n[阶段二] FULL模式 - 逐日全市场补1次 ({len(trading_days)}天)')
        for i, date in enumerate(trading_days):
            print(f'  [{i+1}/{len(trading_days)}] {date} 投递 {len(all_stocks)} 只...')
            download_one_day(date, all_stocks, xtdata, full=True)
            if i < len(trading_days) - 1:
                time.sleep(2)  # 避免指令堆积
        print(f'\n✅ FULL全量指令发射完毕！Tick后台落盘中...')

    else:
        # ── 常规模式：逐日粗筛 + Tick ──
        from logic.data_providers.universe_builder import UniverseBuilder

        total = 0
        for i, date in enumerate(trading_days):
            print(f'\n[{i+1}/{len(trading_days)}] {date}')
            print(f'  [阶段二] 粗筛...')
            try:
                valid_stocks = UniverseBuilder(date).build()
            except Exception as e:
                print(f'  ❌ 粗筛失败: {e}，跳过该日')
                continue

            if not valid_stocks:
                print('  ⚠️ 粗筛后无标的，跳过')
                continue

            print(f'  ✅ {len(valid_stocks)} 只候选 | [阶段三] 投递Tick指令...')
            download_one_day(date, valid_stocks, xtdata, full=False)
            total += len(valid_stocks)
            if i < len(trading_days) - 1:
                time.sleep(1)

        print(f'\n✅ 完成！共处理 {len(trading_days)} 天，投递 {total} 只次Tick指令')


if __name__ == '__main__':
    main()
