# smart_download.py
import time
from xtquant import xtdata

def main():
    print("==================================================")
    print("🚀 [CTO 智能版] 漏斗先导 + Tick 精准狙击下载器")
    print("==================================================")
    
    # 设定目标日期
    target_date = '20260227'
    start_date = '20260110'  # 日K需要多下几天算均线
    
    # 1. 强行接通投研版极速端口
    print("🔌 正在连接投研版端口 58610...")
    try:
        xtdata.connect(port=58610)
        print("✅ 极速通道已打通！")
    except Exception as e:
        print(f"❌ 端口连接失败: {e}")
        return

    # 获取全市场列表
    stock_list = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"🔍 共锁定 {len(stock_list)} 只沪深A股。")

    # ==========================================
    # 第一阶段：全量拉取日K（数据极小，秒下）
    # ==========================================
    print(f"⏬ [阶段一] 开始拉取全市场日K线 (用于粗筛和换手率计算)...")
    xtdata.download_history_data("", '1d', start_time=start_date, end_time=target_date)
    
    print("⏳ 等待日K落盘 (5秒)...")
    time.sleep(5)
    
    # ==========================================
    # 第二阶段：执行 UniverseBuilder 粗筛
    # ==========================================
    print(f"🧠 [阶段二] 启动 TrueDictionary 预热与 UniverseBuilder 粗筛...")
    try:
        from logic.data_providers.true_dictionary import warmup_true_dictionary
        from logic.data_providers.universe_builder import UniverseBuilder
        
        # 预热财务字典(拿流通盘)
        warmup_true_dictionary(stock_list, target_date=target_date)
        
        # 跑粗筛漏斗
        builder = UniverseBuilder(target_date)
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
    for i, stock in enumerate(valid_stocks):
        xtdata.download_history_data(stock, 'tick', start_time=target_date, end_time=target_date)
        
        if (i + 1) % 50 == 0:
            print(f"  ...已投递 {i + 1}/{len(valid_stocks)} 只...")

    print("==================================================")
    print("✅ 智能精准下载指令已全部发射！")
    print(f"💡 请在 QMT 客户端查看 Tick 下载进度。因为只下了 {len(valid_stocks)} 只，速度会极快！")
    print("==================================================")

if __name__ == '__main__':
    main()
