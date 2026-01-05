"""
多股对比模块

提供多只股票的技术指标对比功能
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from logic.data_manager import DataManager
from logic.comparator import StockComparator
from logic.formatter import Formatter
from logic.logger import get_logger
from config import Config

logger = get_logger(__name__)


def render_multi_compare_tab(db: DataManager, config: Config):
    """
    渲染多股对比标签页
    
    Args:
        db: 数据管理器实例
        config: 配置实例
    """
    st.subheader("🔍 多股票技术指标对比")
    
    # 股票代码输入
    compare_symbols_input = st.text_input("输入要对比的股票代码（用逗号分隔）", 
                                         value="600519,000001,600036",
                                         help="例如：600519,000001,600036")
    
    compare_symbols = [s.strip() for s in compare_symbols_input.split(',') if s.strip()]
    
    # 日期范围选择
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=60))
    with col_date2:
        end_date = st.date_input("结束日期", value=datetime.now())
    
    if st.button("开始对比分析") and compare_symbols:
        s_date_str = start_date.strftime("%Y%m%d")
        e_date_str = pd.Timestamp.now().strftime("%Y%m%d")
        
        # 进度条
        progress_bar = st.progress(0)
        progress_text = st.empty()
        
        progress_text.text(f"📊 正在分析 {len(compare_symbols)} 只股票...")
        # 技术指标对比
        comparison_df = StockComparator(db).compare_stocks(compare_symbols, s_date_str, e_date_str)
        progress_bar.progress(50)
        
        progress_text.text("📈 正在生成收益率曲线...")
        # 收益率对比图
        performance_df = StockComparator(db).get_performance_comparison(compare_symbols, s_date_str, e_date_str)
        progress_bar.progress(100)
        
        progress_bar.empty()
        progress_text.empty()
        
        if not comparison_df.empty:
            st.dataframe(comparison_df, width="stretch")
            
            # 收益率对比图
            st.subheader("📈 收益率曲线对比")
            
            if not performance_df.empty:
                fig_perf = go.Figure()
                
                for symbol in performance_df.columns:
                    fig_perf.add_trace(go.Scatter(
                        x=performance_df.index,
                        y=performance_df[symbol],
                        mode='lines',
                        name=symbol
                    ))
                
                fig_perf.update_layout(
                    title="累计收益率对比",
                    xaxis_title="日期",
                    yaxis_title="累计收益率",
                    height=400
                )
                st.plotly_chart(fig_perf, width="stretch")
        else:
            st.warning("未能获取到有效的对比数据，请检查股票代码是否正确。")
    
    # 使用说明
    with st.expander("📖 使用说明"):
        st.markdown("""
        ### 如何使用
        
        1. **输入股票代码**：用逗号分隔多个股票代码，如 `600519,000001,600036`
        2. **选择日期范围**：设置对比的时间段
        3. **点击开始对比**：系统会自动获取数据并生成对比报告
        
        ### 对比指标
        
        - **最新价格**：各股票的最新收盘价
        - **涨跌幅**：指定期间内的涨跌百分比
        - **ATR**：平均真实波幅，衡量波动性
        - **RSI**：相对强弱指标
        - **成交量**：平均成交量
        - **收益率**：累计收益率
        
        💡 **提示**：建议选择同行业或相关性较强的股票进行对比，结果更有参考价值。
        """)