# smart_download.py
"""
智能下载器 - 日K本地读取 + Tick精准狙击
用法:
    python smart_download.py                    # 默认上个交易日
    python smart_download.py 20260303           # 指定单日
    python smart_download.py 20260206 20260302  # 指定日期范围

设计原则:
1. 日K直接读本地，不调用download（投研版已包含全市场日K）
2. 粗筛后只下载有效标的的Tick
"""
import sys
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent))


def main():
    from xtquant import xtdata
    from logic.core.config_manager import get_config_manager
    from logic.utils.calendar_utils import get_latest_completed_trading_day
    
    cfg = get_config_manager()
    
    print("==================================================")
    print("🚀 【CTO 智能版】日K本地读取 + Tick精准狙击")
    print("==================================================")
    
    # 【CTO修复】参数解析：支持日期范围
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    elif len(sys.argv) == 2:
        start_date = end_date = sys.argv[1]
    else:
        start_date = end_date = get_latest_completed_trading_day()
    
    print(f"📅 日期范围: {start_date} ~ {end_date}")
    
    # 【P0修复】端口从配置读取
    port = cfg.get('system_and_risk.qmt_port', 58610)
    print(f"🔌 正在连接投研版端口 {port}...")
    try:
        xtdata.connect(port=port)
        print("✅ 极速通道已打通！")
    except Exception as e:
        print(f"❌ 端口连接失败: {e}")
        return

    # 获取全市场列表
    stock_list = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"🔍 共锁定 {len(stock_list)} 只沪深A股。")

    # ==========================================
    # 【CTO核心优化】阶段一：检查本地日K，不下载！
    # ==========================================
    print(f"📊 [阶段一] 检查本地日K数据...")
    
    # 抽样检查
    sample_stocks = stock_list[:10]
    try:
        sample_data = xtdata.get_local_data(
            field_list=['close', 'amount'],
            stock_list=sample_stocks,
            period='1d',
            start_time=end_date,
            end_time=end_date
        )
        valid_count = sum(1 for s in sample_stocks if s in sample_data and not sample_data[s].empty)
        
        if valid_count >= 5:
            print(f"  ✅ 本地日K数据充足 ({valid_count}/10)，跳过下载")
        else:
            print(f"  ⚠️ 本地日K数据不足 ({valid_count}/10)，尝试补充...")
            try:
                xtdata.download_history_data2(
                    stock_list=stock_list,
                    period='1d',
                    start_time=start_date,
                    end_time=end_date,
                )
                print("  ⏳ 等待日K落盘 (10秒)...")
                time.sleep(10)
            except:
                print("  ⚠️ 日K下载失败，继续使用现有数据...")
    except Exception as e:
        print(f"  ⚠️ 日K检查异常: {e}")
    
    # ==========================================
    # 第二阶段：执行 UniverseBuilder 粗筛
    # ==========================================
    print(f"🧠 [阶段二] 执行 UniverseBuilder 粗筛...")
    try:
        from logic.data_providers.universe_builder import UniverseBuilder
        
        builder = UniverseBuilder(end_date)
        valid_stocks = builder.build()
        print(f"🎯 粗筛完成！从 {len(stock_list)} 只票中，成功过滤出 {len(valid_stocks)} 只活跃标的！")
        
        if not valid_stocks:
            print("⚠️ 粗筛后无标的，今日无需下载 Tick。")
            return
            
    except Exception as e:
        print(f"❌ 粗筛阶段发生异常: {e}")
        import traceback
        traceback.print_exc()
        return

    # ==========================================
    # 第三阶段：对粗筛标的进行 Tick 精准狙击下载
    # ==========================================
    print(f"⏬ [阶段三] 仅对这 {len(valid_stocks)} 只精锐标的发送 Tick 下载指令...")
    
    try:
        xtdata.download_history_data2(
            stock_list=valid_stocks,
            period='tick',
            start_time=start_date,
            end_time=end_date,
        )
    except Exception as e:
        print(f"⚠️ download_history_data2 不可用: {e}，使用单只下载...")
        for i, stock in enumerate(valid_stocks):
            try:
                xtdata.download_history_data(stock, 'tick', start_time=start_date, end_time=end_date)
            except:
                pass
            if (i + 1) % 50 == 0:
                print(f"  ...已投递 {i + 1}/{len(valid_stocks)} 只...")

    # 保存Tick索引
    try:
        from pathlib import Path as PathLib
        index_dir = PathLib(__file__).parent / 'data' / 'tick_index'
        index_dir.mkdir(parents=True, exist_ok=True)
        index_file = index_dir / f"{end_date}.json"
        import json
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump({
                'date': end_date,
                'stocks': valid_stocks,
                'count': len(valid_stocks),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)
    except:
        pass

    print("==================================================")
    print("✅ 智能精准下载指令已全部发射！")
    print(f"💡 Tick正在后台落盘，预计 {len(valid_stocks) * 0.5:.0f} 秒完成")
    print("==================================================")


if __name__ == '__main__':
    main()