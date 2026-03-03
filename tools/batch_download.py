# tools/batch_download.py
"""
CTO 批量下载器 - 日K本地读取 + Tick精准狙击
用法:
    python tools/batch_download.py 20260206 20260302  # 下载日期范围内的Tick
    python tools/batch_download.py 20260303           # 单日下载

设计原则:
1. 日K直接读本地，不调用download（投研版已包含全市场日K）
2. 粗筛后只下载有效标的的Tick
3. 支持日期范围，日K只读一次
"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


def get_trading_days_local(start_date: str, end_date: str) -> list:
    """从本地获取交易日列表"""
    from xtquant import xtdata
    # 获取交易日历
    trading_days = xtdata.get_trading_calendar('SH', start_date, end_date)
    if trading_days:
        return [d.strftime('%Y%m%d') for d in trading_days if d.strftime('%Y%m%d') >= start_date and d.strftime('%Y%m%d') <= end_date]
    
    # 兜底：使用简单的日期推算
    from logic.utils.calendar_utils import get_trading_days_between
    return get_trading_days_between(start_date, end_date)


def check_local_daily_data_exists(date: str, stocks: list) -> int:
    """检查本地日K数据完整性，返回有效数据数量"""
    from xtquant import xtdata
    
    # 抽样检查前10只
    check_stocks = stocks[:10]
    try:
        data = xtdata.get_local_data(
            field_list=['close', 'amount'],
            stock_list=check_stocks,
            period='1d',
            start_time=date,
            end_time=date
        )
        
        valid_count = 0
        for stock in check_stocks:
            if stock in data and not data[stock].empty:
                try:
                    amount = float(data[stock].iloc[-1].get('amount', 0))
                    if amount > 0:
                        valid_count += 1
                except:
                    pass
        return valid_count
    except:
        return 0


def run_coarse_filter(date: str, stocks: list) -> list:
    """执行粗筛，返回有效标的列表"""
    from logic.data_providers.universe_builder import UniverseBuilder
    
    try:
        builder = UniverseBuilder(target_date=date)
        valid_stocks = builder.build()
        return valid_stocks if valid_stocks else []
    except Exception as e:
        print(f"  ⚠️ 粗筛异常: {e}")
        return []


def download_tick_async(stocks: list, date: str):
    """异步发送Tick下载指令"""
    from xtquant import xtdata
    
    try:
        # 批量下载（异步）
        xtdata.download_history_data2(
            stock_list=stocks,
            period='tick',
            start_time=date,
            end_time=date,
        )
        return True
    except Exception as e:
        # 兜底：单只下载
        print(f"  ⚠️ download_history_data2不可用，使用单只下载...")
        for stock in stocks:
            try:
                xtdata.download_history_data(stock, 'tick', start_time=date, end_time=date)
            except:
                pass
        return True


def save_tick_index(date: str, stocks: list, success: bool = True):
    """保存Tick数据索引"""
    import json
    from pathlib import Path
    
    index_dir = Path(__file__).parent.parent / 'data' / 'tick_index'
    index_dir.mkdir(parents=True, exist_ok=True)
    
    index_file = index_dir / f"{date}.json"
    index_data = {
        'date': date,
        'stocks': stocks,
        'count': len(stocks),
        'status': 'success' if success else 'pending',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)


def main():
    from xtquant import xtdata
    from logic.core.config_manager import get_config_manager
    
    print("=" * 60)
    print("🚀 【CTO 批量下载器】日K本地读取 + Tick精准狙击")
    print("=" * 60)
    
    # 解析参数
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    elif len(sys.argv) == 2:
        start_date = end_date = sys.argv[1]
    else:
        # 默认上个交易日
        from logic.utils.calendar_utils import get_latest_completed_trading_day
        start_date = end_date = get_latest_completed_trading_day()
    
    print(f"📅 日期范围: {start_date} ~ {end_date}")
    
    # 连接QMT
    cfg = get_config_manager()
    port = cfg.get('system_and_risk.qmt_port', 58610)
    print(f"🔌 连接投研版端口 {port}...")
    
    try:
        xtdata.connect(port=port)
        print("✅ 连接成功！")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return
    
    # 获取交易日列表
    trading_days = get_trading_days_local(start_date, end_date)
    print(f"📆 共 {len(trading_days)} 个交易日: {trading_days[0] if trading_days else 'N/A'} ~ {trading_days[-1] if trading_days else 'N/A'}")
    
    if not trading_days:
        print("❌ 无交易日，退出")
        return
    
    # 获取全市场列表（一次获取，复用）
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"🔍 全市场共 {len(all_stocks)} 只A股")
    
    # ==========================================
    # 【CTO核心优化】阶段一：检查日K本地数据，不下载！
    # ==========================================
    print(f"\n📊 [阶段一] 检查本地日K数据...")
    
    # 抽样检查第一个交易日
    sample_date = trading_days[0]
    valid_count = check_local_daily_data_exists(sample_date, all_stocks)
    
    if valid_count < 5:
        print(f"  ⚠️ 本地日K数据不足 ({valid_count}/10)，尝试补充下载...")
        # 仅在此情况下才下载日K
        try:
            xtdata.download_history_data2(
                stock_list=all_stocks,
                period='1d',
                start_time=start_date,
                end_time=end_date,
            )
            print("  ⏳ 等待日K落盘 (10秒)...")
            time.sleep(10)
        except:
            print("  ⚠️ 日K下载失败，继续使用现有数据...")
    else:
        print(f"  ✅ 本地日K数据充足 ({valid_count}/10)，跳过下载")
    
    # ==========================================
    # 阶段二+三：逐日粗筛 + Tick下载
    # ==========================================
    total_candidates = 0
    
    for i, date in enumerate(trading_days):
        print(f"\n[{i+1}/{len(trading_days)}] 处理 {date}...")
        
        # 粗筛
        print(f"  🔍 执行粗筛...")
        valid_stocks = run_coarse_filter(date, all_stocks)
        
        if not valid_stocks:
            print(f"  ⏭️ 粗筛后无标的，跳过")
            save_tick_index(date, [], success=False)
            continue
        
        print(f"  ✅ 粗筛完成: {len(valid_stocks)} 只候选")
        total_candidates += len(valid_stocks)
        
        # 发送Tick下载指令（异步）
        print(f"  📥 发送Tick下载指令...")
        download_tick_async(valid_stocks, date)
        
        # 保存索引
        save_tick_index(date, valid_stocks)
        
        # 避免指令堆积
        time.sleep(1)
    
    # ==========================================
    # 完成
    # ==========================================
    print("\n" + "=" * 60)
    print(f"✅ 批量下载完成！")
    print(f"   📅 处理交易日: {len(trading_days)} 天")
    print(f"   📊 粗筛候选: {total_candidates} 只次")
    print(f"   💡 Tick正在后台落盘，请稍后验证")
    print("=" * 60)


if __name__ == '__main__':
    main()
