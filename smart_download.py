# smart_download.py
"""
智能下载器 - 漏斗先导 + Tick 精准狙击
用法:
    python smart_download.py                    # 默认上个交易日
    python smart_download.py 20260303           # 指定目标日期
    python smart_download.py 20260303 20260110  # 指定目标日期和历史起始日
"""
import sys
import time
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent))


def main():
    from xtquant import xtdata
    from logic.core.config_manager import get_config_manager
    from logic.utils.calendar_utils import get_latest_completed_trading_day
    
    cfg = get_config_manager()
    
    print("==================================================")
    print("🚀 [CTO 智能版] 漏斗先导 + Tick 精准狙击下载器")
    print("==================================================")
    
    # 【P0修复】日期从命令行读取，不写死
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = get_latest_completed_trading_day()
    
    if len(sys.argv) > 2:
        start_date = sys.argv[2]
    else:
        # 【审计修复】默认补近45天（约30个交易日）的历史缺口
        from datetime import datetime, timedelta
        start_date = (datetime.strptime(target_date, '%Y%m%d') 
                      - timedelta(days=45)).strftime('%Y%m%d')
    
    print(f"📅 目标日期: {target_date} | 历史起始: {start_date}")
    
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
    # 第一阶段：全量拉取日K（数据极小，秒下）
    # ==========================================
    print(f"⏬ [阶段一] 开始拉取全市场日K线 (用于粗筛和换手率计算)...")
    
    # 【P0修复】使用 download_history_data2 替代空字符串版本
    try:
        xtdata.download_history_data2(
            stock_list=stock_list,
            period='1d',
            start_time=start_date,
            end_time=target_date,
            incrementally=True
        )
    except Exception as e:
        # 兜底：如果 download_history_data2 不可用，使用单只下载
        print(f"⚠️ download_history_data2 不可用: {e}，使用单只下载...")
        for stock in stock_list[:100]:  # 先下载前100只测试
            try:
                xtdata.download_history_data(stock, '1d', start_time=start_date, end_time=target_date)
            except:
                pass
    
    print("⏳ 等待日K落盘 (3秒)...")
    time.sleep(3)
    
    # ==========================================
    # 第二阶段：执行 UniverseBuilder 粗筛（先筛再warmup）
    # ==========================================
    print(f"🧠 [阶段二] 执行 UniverseBuilder 粗筛...")
    try:
        from logic.data_providers.universe_builder import UniverseBuilder
        
        # 【P1修复】先粗筛，再 warmup（顺序必须对）
        builder = UniverseBuilder(target_date)
        valid_stocks = builder.build()
        print(f"🎯 粗筛完成！从 {len(stock_list)} 只票中，成功过滤出 {len(valid_stocks)} 只活跃标的！")
        
        if not valid_stocks:
            print("⚠️ 粗筛后无标的，今日无需下载 Tick。")
            return
        
        # 【P1修复】只对粗筛后的标的进行 warmup
        print(f"🔥 预热 TrueDictionary (仅 {len(valid_stocks)} 只候选股)...")
        from logic.data_providers.true_dictionary import warmup_true_dictionary
        warmup_true_dictionary(valid_stocks, target_date=target_date)
            
    except Exception as e:
        print(f"❌ 粗筛阶段发生异常: {e}")
        import traceback
        traceback.print_exc()
        return

    # ==========================================
    # 第三阶段：对粗筛标的进行 Tick 精准狙击下载
    # ==========================================
    print(f"⏬ [阶段三] 仅对这 {len(valid_stocks)} 只精锐标的发送 Tick 下载指令...")
    
    def on_progress(progress):
        """下载进度回调"""
        print(f"  📊 Tick下载进度: {progress}")
    
    try:
        # 【P0修复】使用 download_history_data2 批量下载
        xtdata.download_history_data2(
            stock_list=valid_stocks,
            period='tick',
            start_time=target_date,
            end_time=target_date,
            incrementally=True,
            callback=on_progress
        )
    except Exception as e:
        # 兜底：单只下载
        print(f"⚠️ download_history_data2 不可用: {e}，使用单只下载...")
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