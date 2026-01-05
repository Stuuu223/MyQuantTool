"""
龙虎榜模块

提供龙虎榜数据分析功能
"""

import streamlit as st
import pandas as pd
from logic.algo import QuantAlgo
from logic.formatter import Formatter
from logic.logger import get_logger

logger = get_logger(__name__)


def render_long_hu_bang_tab(db, config):
    """渲染龙虎榜标签页"""
    st.subheader("🏆 龙虎榜分析")
    st.caption("监控市场活跃股票和机构动向")
    
    # 日期选择
    lhb_date = st.date_input("选择日期", value=pd.Timestamp.now().date())
    
    # 自动加载数据
    with st.spinner('正在获取龙虎榜数据...'):
        date_str = lhb_date.strftime("%Y%m%d")
        lhb_data = QuantAlgo.get_lhb_data(date_str)
        
        if lhb_data['数据状态'] == '正常':
            stocks = lhb_data['股票列表']
            
            # 显示数据日期
            if '数据日期' in lhb_data:
                st.info(f"📅 数据日期：{lhb_data['数据日期']}")
            
            # 排序选项
            col_sort1, col_sort2 = st.columns(2)
            with col_sort1:
                sort_by = st.selectbox("排序方式", ["净买入额", "涨跌幅", "收盘价"])
            with col_sort2:
                sort_order = st.selectbox("排序顺序", ["降序", "升序"])
            
            # 排序
            reverse_order = (sort_order == "降序")
            if sort_by == "净买入额":
                stocks_sorted = sorted(stocks, key=lambda x: x['龙虎榜净买入'], reverse=reverse_order)
            elif sort_by == "涨跌幅":
                stocks_sorted = sorted(stocks, key=lambda x: x['涨跌幅'], reverse=reverse_order)
            else:  # 收盘价
                stocks_sorted = sorted(stocks, key=lambda x: x['收盘价'], reverse=reverse_order)
            
            # 格式化数据用于显示
            display_stocks = []
            for stock in stocks_sorted:
                display_stocks.append({
                    '代码': stock['代码'],
                    '名称': stock['名称'],
                    '收盘价': stock['收盘价'],
                    '涨跌幅': stock['涨跌幅'],
                    '龙虎榜净买入': Formatter.format_amount(stock['龙虎榜净买入']),
                    '上榜原因': stock['上榜原因']
                })
            
            # 显示数据表格
            st.dataframe(
                pd.DataFrame(display_stocks),
                column_config={
                    '代码': st.column_config.TextColumn('代码', width='small'),
                    '名称': st.column_config.TextColumn('名称', width='medium'),
                    '收盘价': st.column_config.NumberColumn('收盘价', format='%.2f'),
                    '涨跌幅': st.column_config.NumberColumn('涨跌幅', format='%.2f%%'),
                    '龙虎榜净买入': st.column_config.TextColumn('净买入', width='medium'),
                    '上榜原因': st.column_config.TextColumn('上榜原因', width='large')
                },
                width="stretch",
                hide_index=True
            )
            
            # 龙虎榜净买入排行
            st.subheader("📈 龙虎榜净买入排行")
            top_stocks = sorted(stocks, key=lambda x: x['龙虎榜净买入'], reverse=True)[:10]
            
            for i, stock in enumerate(top_stocks, 1):
                with st.container():
                    cols = st.columns([1, 3, 2, 2, 3])
                    cols[0].write(f"**{i}**")
                    cols[1].write(f"**{stock['名称']}** ({stock['代码']})")
                    cols[2].metric("净买入", Formatter.format_amount(stock['龙虎榜净买入']))
                    cols[3].metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                    cols[4].caption(stock['上榜原因'])
                    st.divider()
            
            # 龙虎榜解析
            st.divider()
            st.subheader("📊 龙虎榜深度解析")
            
            with st.spinner('正在分析龙虎榜数据...'):
                summary = QuantAlgo.analyze_lhb_summary()
                
                if summary['数据状态'] == '正常':
                    # 总体数据
                    col1, col2, col3 = st.columns(3)
                    col1.metric("上榜股票数量", f"{summary['上榜股票数量']} 只")
                    col2.metric("龙虎榜净买入总额", Formatter.format_amount(summary['龙虎榜净买入总额']))
                    col3.metric("总成交额", Formatter.format_amount(summary['总成交额']))                    
                    # 上榜原因统计
                    if summary['上榜原因统计']:
                        st.subheader("🔍 上榜原因统计")
                        reason_df = pd.DataFrame([
                            {'上榜原因': reason, '数量': count}
                            for reason, count in summary['上榜原因统计'].items()
                        ])
                        st.dataframe(reason_df, width="stretch", hide_index=True)
                    
                    # 机构统计
                    if summary['机构统计'] is not None and not summary['机构统计'].empty:
                        st.subheader("🏢 机构席位统计")
                        st.dataframe(summary['机构统计'].head(10), width="stretch")
                    
                    # 活跃营业部
                    if summary['活跃营业部'] is not None and not summary['活跃营业部'].empty:
                        st.subheader("🏪 活跃营业部")
                        st.dataframe(summary['活跃营业部'].head(10), width="stretch")
                    
                    # 资金流向分析
                    st.subheader("💰 资金流向分析")
                    net_buy_ratio = summary['龙虎榜净买入总额'] / summary['总成交额'] * 100 if summary['总成交额'] > 0 else 0
                    
                    if net_buy_ratio > 5:
                        st.success(f"✅ 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，主力资金积极介入")
                    elif net_buy_ratio > 0:
                        st.info(f"📊 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，资金面偏多")
                    elif net_buy_ratio > -5:
                        st.warning(f"⚠️ 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，资金面偏空")
                    else:
                        st.error(f"❌ 龙虎榜资金净买入占比 {net_buy_ratio:.2f}%，主力资金大幅流出")
                else:
                    st.error(f"❌ {summary['数据状态']}")
                    if '错误信息' in summary:
                        st.caption(summary['错误信息'])
        else:
            st.error(f"❌ {lhb_data['数据状态']}")
            if '错误信息' in lhb_data:
                st.caption(lhb_data['错误信息'])
            else:
                st.caption(lhb_data['说明'])
        
        # 龙虎榜质量分析
        st.divider()
        st.subheader("🎯 龙虎榜质量分析")
        st.caption("区分好榜和坏榜，推荐值得次日介入的股票")
        
        with st.spinner('正在分析龙虎榜质量...'):
            quality_analysis = QuantAlgo.analyze_lhb_quality()
            
            if quality_analysis['数据状态'] == '正常':
                stats = quality_analysis['统计']
                
                # 显示统计
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("优质榜", f"{stats['优质榜数量']} 只", delta="强烈推荐")
                col2.metric("良好榜", f"{stats['良好榜数量']} 只", delta="推荐关注")
                col3.metric("一般榜", f"{stats['劣质榜数量']} 只", delta="谨慎观望")
                col4.metric("总数", f"{stats['总数']} 只")
                
                # 推荐股票
                st.subheader("⭐ 推荐关注（优质榜）")
                recommended_stocks = [s for s in quality_analysis['股票分析'] if s['评分'] >= 70]
                
                if recommended_stocks:
                    for stock in recommended_stocks:
                        with st.expander(f"{stock['榜单质量']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("收盘价", f"¥{stock['收盘价']:.2f}")
                            col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                            col3.metric("净买入", Formatter.format_amount(stock['净买入']))
                            
                            st.write("**上榜原因：**", stock['上榜原因'])
                            st.write("**评分原因：**", "、".join(stock['评分原因']))
                            st.success(f"📈 推荐操作：{stock['推荐']}")
                else:
                    st.info("暂无优质榜单")
                
                # 良好榜
                if len(recommended_stocks) < 10:
                    st.subheader("🟡 良好榜（可关注）")
                    good_stocks = [s for s in quality_analysis['股票分析'] if 50 <= s['评分'] < 70]
                    
                    if good_stocks:
                        for stock in good_stocks[:5]:  # 只显示前5只
                            with st.expander(f"{stock['榜单质量']} {stock['名称']} ({stock['代码']}) - 评分: {stock['评分']}"):
                                col1, col2, col3 = st.columns(3)
                                col1.metric("收盘价", f"¥{stock['收盘价']:.2f}")
                                col2.metric("涨跌幅", f"{stock['涨跌幅']:.2f}%")
                                col3.metric("净买入", format_amount(stock['净买入']))
                                
                                st.write("**上榜原因：**", stock['上榜原因'])
                                st.write("**评分原因：**", "、".join(stock['评分原因']))
                                st.info(f"📊 推荐操作：{stock['推荐']}")
                
                # 劣质榜（可选显示）
                with st.expander("🔴 劣质榜（不建议介入）"):
                    poor_stocks = [s for s in quality_analysis['股票分析'] if s['评分'] < 30]
                    if poor_stocks:
                        st.dataframe(
                            pd.DataFrame([
                                {
                                    '代码': s['代码'],
                                    '名称': s['名称'],
                                    '评分': s['评分'],
                                    '上榜原因': s['上榜原因'],
                                    '推荐': s['推荐']
                                }
                                for s in poor_stocks
                            ]),
                            width="stretch",
                            hide_index=True
                            )
                    else:
                        st.info("暂无劣质榜单")
                
                # 评分说明
                st.divider()
                st.caption("**评分说明：**")
                st.caption("- 净买入额（30分）：净买入>1亿得30分，>5000万得20分，>0得10分")
                st.caption("- 涨跌幅（20分）：3-7%得20分，7-10%得10分，>10%扣10分")
                st.caption("- 成交额（15分）：>5亿得15分，>2亿得10分，>1亿得5分")
                st.caption("- 上榜原因（20分）：机构买入等优质原因得20分，ST等劣质原因扣20分")
                st.caption("- 净买入占比（15分）：>10%得15分，>5%得10分，>0得5分")
                st.caption("- 优质榜（≥70分）：强烈推荐次日介入")
                st.caption("- 良好榜（50-69分）：推荐关注")
                st.caption("- 一般榜（30-49分）：谨慎观望")
                st.caption("- 劣质榜（<30分）：不建议介入")
            else:
                st.error(f"❌ {quality_analysis['数据状态']}")

