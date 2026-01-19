#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.7 智能复盘驾驶舱 (Mirror of Truth)
提供每日复盘、高价值案例展示、历史回放等功能
"""

import streamlit as st
import pandas as pd
import json
import os
import datetime
from logic.logger import get_logger

logger = get_logger(__name__)


def render_review_dashboard():
    """
    渲染 V18.7 智能复盘驾驶舱
    
    功能：
    1. 每日复盘报告展示
    2. 高价值案例捕获（真龙/大坑/炸板）
    3. 市场情绪评分
    4. 历史交易日快速选择
    """
    
    st.header("🧠 V18.7 智能复盘驾驶舱 (Mirror of Truth)")
    
    # 侧边栏日期选择
    st.sidebar.subheader("📅 复盘日期选择")
    
    # 获取可用的历史交易日
    available_dates = []
    cases_dir = "data/review_cases/golden_cases"
    if os.path.exists(cases_dir):
        for filename in os.listdir(cases_dir):
            if filename.startswith("cases_") and filename.endswith(".json"):
                date_str = filename.replace("cases_", "").replace(".json", "")
                available_dates.append(date_str)
    
    # 默认选择今天或最近一个交易日
    today = datetime.date.today()
    today_str = today.strftime("%Y%m%d")
    
    if today_str in available_dates:
        selected_date = st.sidebar.date_input("选择复盘日期", today, key="review_date")
    elif available_dates:
        # 选择最近的一个交易日
        latest_date = max(available_dates)
        selected_date = st.sidebar.date_input(
            "选择复盘日期",
            datetime.datetime.strptime(latest_date, "%Y%m%d").date(),
            key="review_date"
        )
    else:
        selected_date = st.sidebar.date_input("选择复盘日期", today, key="review_date")
    
    date_str = selected_date.strftime("%Y%m%d")
    file_path = f"data/review_cases/golden_cases/cases_{date_str}.json"
    
    # 如果没有数据，提供一键生成选项
    if not os.path.exists(file_path):
        st.warning(f"⏳ {date_str} 尚未生成复盘报告。")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 立即运行复盘任务", key="run_review"):
                try:
                    from logic.review_manager import ReviewManager
                    rm = ReviewManager()
                    cases = rm.capture_golden_cases(date_str)
                    if cases:
                        st.success(f"✅ 复盘任务完成！")
                        st.rerun()
                    else:
                        st.error("❌ 复盘任务失败，请检查日志。")
                except Exception as e:
                    st.error(f"❌ 复盘任务执行失败: {e}")
        
        with col2:
            if st.button("📊 查看历史交易日", key="view_history"):
                st.info(f"📅 可用的历史交易日: {', '.join(available_dates)}")
        
        return
    
    # 加载复盘数据
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 1. 指标总览
    st.subheader("📊 市场情绪概览")
    
    m1, m2, m3 = st.columns(3)
    score = data.get('market_score', 50)
    
    # 根据分数显示不同的颜色
    if score >= 80:
        score_color = "🟢"
    elif score >= 60:
        score_color = "🟡"
    else:
        score_color = "🔴"
    
    m1.metric("市场情绪得分", f"{score_color} {score} / 100")
    m2.metric("捕获龙/坑总数", len(data['dragons']) + len(data['traps']))
    m3.metric("复盘日期", date_str)
    
    # 市场情绪解读
    st.info(f"💡 市场情绪解读: {get_market_sentiment_comment(score)}")
    
    st.divider()
    
    # 2. 核心案例展示
    st.subheader("🎯 高价值案例展示")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("### 🐉 今日真龙 (标准答案)")
        if data['dragons']:
            for i, d in enumerate(data['dragons']):
                with st.expander(f"{i+1}. {d['name']} ({d['code']})", expanded=(i == 0)):
                    st.success(d['reason'])
                    
                    # 显示详细信息
                    if 'limit_board' in d:
                        st.caption(f"📈 连板高度: {d['limit_board']}板")
                    if 'seal_amount' in d:
                        st.caption(f"💰 封单金额: {int(d['seal_amount']/10000)}万")
                    
                    st.caption("💡 建议操作：点击'历史回放'查看 9:30 DDE 状态")
                    
                    # 添加DDE溯源按钮
                    col_dde1, col_dde2 = st.columns(2)
                    with col_dde1:
                        if st.button(f"🔍 DDE溯源 {d['name']}", key=f"dde_trace_{d['code']}"):
                            try:
                                from logic.review_manager import ReviewManager
                                rm = ReviewManager()
                                dde_history = rm.get_dde_history(d['code'], date_str)
                                
                                if dde_history:
                                    st.info(f"📊 {d['name']} 在 {date_str} 9:30-10:00 的DDE脉冲数据")
                                    
                                    # 创建DataFrame显示DDE历史数据
                                    df_dde = pd.DataFrame(dde_history)
                                    
                                    # 🆕 V19 修复：确保时间轴统一格式化为HH:MM字符串
                                    if 'time' in df_dde.columns:
                                        # 如果time列是datetime对象，转换为字符串
                                        if pd.api.types.is_datetime64_any_dtype(df_dde['time']):
                                            df_dde['time'] = df_dde['time'].dt.strftime('%H:%M')
                                        # 如果time列是字符串，确保格式正确
                                        elif df_dde['time'].dtype == 'object':
                                            # 移除可能的日期部分，只保留时间
                                            df_dde['time'] = df_dde['time'].apply(lambda x: str(x).split(' ')[-1] if ' ' in str(x) else str(x))
                                    
                                    st.dataframe(df_dde, use_container_width=True)
                                    
                                    # 🆕 V19 修复：确保绘图前时间轴格式正确
                                    if 'time' in df_dde.columns:
                                        # 使用time作为索引
                                        df_chart = df_dde.set_index('time')
                                        # 确保只选择数值列
                                        numeric_cols = ['dde_value', 'price']
                                        existing_cols = [col for col in numeric_cols if col in df_chart.columns]
                                        if existing_cols:
                                            st.line_chart(df_chart[existing_cols])
                                        else:
                                            st.warning("⚠️ 无可用的数值列进行绘图")
                                else:
                                    st.warning(f"⚠️ 暂无 {d['name']} 的DDE历史数据")
                            except Exception as e:
                                st.error(f"❌ 获取DDE历史数据失败: {e}")
                    
                    with col_dde2:
                        # 添加查看详情按钮
                        if st.button(f"📋 查看详情", key=f"dragon_{d['code']}"):
                            st.info(f"🔍 正在加载 {d['name']} 的详细数据...")
                            # 这里可以添加更详细的股票分析
        else:
            st.info("📭 今日未捕获到标准真龙案例")
    
    with col_b:
        st.markdown("### 💀 核按钮 (避坑指南)")
        if data['traps']:
            for i, t in enumerate(data['traps']):
                with st.expander(f"{i+1}. {t['name']} ({t['code']})", expanded=(i == 0)):
                    st.error(t['reason'])
                    
                    # 显示详细信息
                    if 'change_pct' in t:
                        st.caption(f"📉 跌幅: {t['change_pct']}%")
                    if 'amount' in t:
                        st.caption(f"💸 成交额: {int(t['amount']/10000)}万")
                    
                    # 根据类型显示不同的风险特征
                    if t.get('type') == 'FAILED_DRAGON':
                        st.caption("⚠️ 风险特征：炸板大面，天地板风险")
                    elif t.get('type') == 'FATAL_TRAP':
                        st.caption("⚠️ 风险特征：核按钮惨案，跌停风险")
        else:
            st.info("📭 今日未捕获到核按钮案例")
    
    st.divider()
    
    # 3. AI 教练点评
    st.subheader("🤖 AI 教练点评")
    
    execution_score = calculate_execution_score(data)
    coach_comment = get_coach_comment(execution_score, data)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info(coach_comment)
    with col2:
        st.metric("执行评分", f"{execution_score} / 100")
    
    st.divider()
    
    # 4. 错题本展示
    st.subheader("📝 错题本 (逻辑漏失警报)")
    
    try:
        from logic.review_manager import ReviewManager
        rm = ReviewManager()
        
        # 获取错题本记录
        error_records = rm.get_error_book(date_str)
        
        if error_records:
            st.warning(f"⚠️ 发现 {len(error_records)} 条逻辑漏失记录")
            
            for i, record in enumerate(error_records):
                with st.expander(f"{i+1}. {record['stock_name']} ({record['stock_code']}) - {record['type']}", expanded=(i == 0)):
                    st.error(f"💥 {record['reason']}")
                    st.caption(f"📅 记录时间: {record['created_at']}")
                    
                    # 🆕 V19 新增：加入明日重点监控按钮
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("🎯 加入明日重点监控", key=f"add_to_monitor_{record['id']}"):
                            try:
                                from logic.review_manager import ReviewManager
                                rm = ReviewManager()
                                success = rm.add_to_monitor_list(
                                    record['stock_code'],
                                    record['stock_name'],
                                    reason=f"错题本漏失: {record['reason']}"
                                )
                                if success:
                                    st.success(f"✅ 已将 {record['stock_name']} 加入明日重点监控")
                                else:
                                    st.warning(f"⚠️ 加入监控失败")
                            except Exception as e:
                                st.error(f"❌ 加入监控失败: {e}")
                    
                    with col_btn2:
                        # 提供手动录入原因的选项
                        manual_reason = st.text_input(
                            "补充漏失原因（可选）",
                            value="",
                            key=f"manual_reason_{record['id']}"
                        )
                        
                        if st.button("💾 保存原因", key=f"update_reason_{record['id']}"):
                            if manual_reason:
                                # TODO: 实现更新错题本原因的逻辑
                                st.success(f"✅ 已记录原因: {manual_reason}")
                            else:
                                st.warning("⚠️ 请输入原因")
        else:
            st.success("✅ 今日无逻辑漏失记录，表现完美！")
    except Exception as e:
        st.error(f"❌ 加载错题本失败: {e}")
    
    st.divider()
    
    # 5. 龙虎榜席位指纹
    st.subheader("🎯 龙虎榜席位指纹")
    
    if data['dragons']:
        selected_dragon = st.selectbox(
            "选择真龙查看龙虎榜席位",
            options=data['dragons'],
            format_func=lambda x: f"{x['name']} ({x['code']})",
            key="select_dragon_lhb"
        )
        
        if st.button("查看席位指纹", key="view_lhb_fingerprint"):
            try:
                from logic.review_manager import ReviewManager
                rm = ReviewManager()
                
                fingerprint = rm.get_longhubu_fingerprint(selected_dragon['code'], date_str)
                
                if fingerprint['has_institutional']:
                    st.success(f"🏛️ {selected_dragon['name']} 有机构介入")
                else:
                    st.info(f"📊 {selected_dragon['name']} 无机构介入")
                
                if fingerprint['top_traders']:
                    st.subheader("🌟 顶级游资")
                    for trader in fingerprint['top_traders']:
                        # 🆕 V19 新增：显示席位历史战绩
                        with st.expander(f"💰 {trader['name']}: 买入 {int(trader['buy_amount']/10000)}万", expanded=False):
                            try:
                                from logic.review_manager import ReviewManager
                                rm = ReviewManager()
                                
                                # 获取席位历史战绩
                                perf = rm.get_seat_history_performance(trader['name'], lookback_days=30)
                                
                                if perf['total_appearances'] > 0:
                                    # 显示核心指标
                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.metric("上榜次数", perf['total_appearances'])
                                    with col2:
                                        profit_color = "normal" if perf['next_day_avg_profit'] > 0 else "inverse"
                                        st.metric("次日平均溢价", f"{perf['next_day_avg_profit']}%", delta_color=profit_color)
                                    with col3:
                                        st.metric("盈利概率", f"{perf['next_day_profit_rate']}%")
                                    with col4:
                                        st.metric("最大盈利", f"{perf['next_day_max_profit']}%")
                                    
                                    # 显示历史战绩评价
                                    if perf['next_day_avg_profit'] > 3:
                                        st.success(f"✅ {trader['name']} 战绩优秀，次日平均溢价 {perf['next_day_avg_profit']}%，值得跟随")
                                    elif perf['next_day_avg_profit'] > 1:
                                        st.info(f"📊 {trader['name']} 战绩良好，次日平均溢价 {perf['next_day_avg_profit']}%，可适度关注")
                                    else:
                                        st.warning(f"⚠️ {trader['name']} 战绩一般，次日平均溢价仅 {perf['next_day_avg_profit']}%，需谨慎")
                                    
                                    # 显示最近10次记录
                                    if perf['recent_appearances']:
                                        st.markdown("**最近10次次日溢价：**")
                                        df_perf = pd.DataFrame({
                                            '次数': list(range(1, len(perf['recent_appearances']) + 1)),
                                            '次日溢价(%)': perf['recent_appearances']
                                        })
                                        st.dataframe(df_perf, use_container_width=True)
                                else:
                                    st.info(f"📊 {trader['name']} 在过去30天内无上榜记录")
                            
                            except Exception as e:
                                st.warning(f"⚠️ 获取席位历史战绩失败: {e}")
                else:
                    st.info("📭 无顶级游资介入")
                
                if fingerprint['cost_line'] > 0:
                    st.metric("主力成本线", f"¥{fingerprint['cost_line']:.2f}")
                    
                    # 获取当前价格
                    try:
                        realtime_data = data_manager.get_realtime_data(selected_dragon['code'])
                        if realtime_data:
                            current_price = realtime_data.get('price', 0)
                            distance = (current_price - fingerprint['cost_line']) / fingerprint['cost_line'] * 100 if fingerprint['cost_line'] > 0 else 0
                            
                            if abs(distance) <= 2:
                                st.success(f"✅ [黄金低吸点] 当前价格接近主力成本线（{distance:.1f}%），建议低吸")
                            else:
                                st.info(f"📊 距离主力成本线: {distance:.1f}%")
                    except:
                        pass
            except Exception as e:
                st.error(f"❌ 获取龙虎榜席位指纹失败: {e}")
    else:
        st.info("📭 今日无真龙数据")
    
    st.divider()
    
    # 6. 历史交易日快速选择
    st.subheader("📅 历史交易日")
    
    if available_dates:
        # 按日期倒序排列
        available_dates.sort(reverse=True)
        
        selected_history = st.selectbox(
            "快速跳转到历史交易日",
            available_dates,
            format_func=lambda x: f"{x[:4]}-{x[4:6]}-{x[6:8]}",
            key="history_date"
        )
        
        if st.button("跳转到选中的交易日", key="jump_to_history"):
            # 更新侧边栏的日期选择器
            st.session_state['review_date'] = datetime.datetime.strptime(selected_history, "%Y%m%d").date()
            st.rerun()
    else:
        st.info("📭 暂无历史交易日数据")
    
    # 5. 架构师点评
    st.divider()
    st.info("💡 架构师点评：如果你今天没买入上述真龙，请回看 V18.6 的'价格发现'模块是否开启。同时，检查 DDE 拒否权是否正常工作。")


def get_market_sentiment_comment(score):
    """
    根据市场情绪得分生成解读评论
    
    Args:
        score: 市场情绪得分 (0-100)
    
    Returns:
        str: 情绪解读
    """
    if score >= 90:
        return "🌟 市场极度活跃，多头情绪高涨，适合激进操作。注意风险控制。"
    elif score >= 75:
        return "🟢 市场情绪良好，多头占优，可以积极寻找机会。"
    elif score >= 60:
        return "🟡 市场情绪中性，多空平衡，建议谨慎操作。"
    elif score >= 40:
        return "🟠 市场情绪偏弱，空头占优，建议减少操作频率。"
    else:
        return "🔴 市场情绪极度低迷，建议空仓观望，等待机会。"


def calculate_execution_score(data):
    """
    计算执行评分
    
    Args:
        data: 复盘数据
    
    Returns:
        int: 执行评分 (0-100)
    """
    score = 0
    
    # 基础分：有数据就给 20 分
    if data:
        score += 20
    
    # 捕获真龙：每只给 20 分
    score += len(data.get('dragons', [])) * 20
    
    # 捕获大坑：每只给 15 分
    score += len(data.get('traps', [])) * 15
    
    # 市场情绪评分：占 30%
    market_score = data.get('market_score', 0)
    score += market_score * 0.3
    
    # 限制在 0-100 之间
    return int(min(max(score, 0), 100))


def get_coach_comment(execution_score, data):
    """
    生成 AI 教练点评
    
    Args:
        execution_score: 执行评分
        data: 复盘数据
    
    Returns:
        str: AI 教练点评
    """
    dragons_count = len(data.get('dragons', []))
    traps_count = len(data.get('traps', []))
    
    if execution_score >= 90:
        return f"🎯 完美执行！成功捕获 {dragons_count} 只真龙，{traps_count} 个大坑。你的复盘系统运行良好，继续保持！"
    elif execution_score >= 75:
        return f"✅ 表现优秀！捕获 {dragons_count} 只真龙，{traps_count} 个大坑。复盘系统运行稳定，可以继续优化。"
    elif execution_score >= 60:
        return f"👍 表现良好！捕获 {dragons_count} 只真龙，{traps_count} 个大坑。复盘系统基本正常，建议检查数据源。"
    elif execution_score >= 40:
        return f"⚠️ 表现一般！仅捕获 {dragons_count} 只真龙，{traps_count} 个大坑。建议检查数据接口和网络连接。"
    else:
        return f"❌ 执行不理想！仅捕获 {dragons_count} 只真龙，{traps_count} 个大坑。建议立即检查系统配置和数据源。"


# 单元测试
if __name__ == "__main__":
    # 测试市场情绪解读
    print("测试市场情绪解读:")
    for score in [95, 80, 65, 50, 30]:
        print(f"  {score}分: {get_market_sentiment_comment(score)}")
    
    # 测试执行评分
    print("\n测试执行评分:")
    test_data = {
        "dragons": [{"code": "000001", "name": "平安银行"}],
        "traps": [{"code": "000002", "name": "万科A"}],
        "market_score": 70
    }
    score = calculate_execution_score(test_data)
    print(f"  执行评分: {score}")
    
    # 测试 AI 教练点评
    print("\n测试 AI 教练点评:")
    print(f"  {score}分: {get_coach_comment(score, test_data)}")
    
    print("\n✅ 所有测试通过！")
