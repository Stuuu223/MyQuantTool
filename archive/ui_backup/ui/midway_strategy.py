"""
半路战法UI模块 - V19 20cm加速战法

核心功能：
- 专攻创业板(300)和科创板(688)的20cm标的
- 捕捉分时均线支撑后的二次加速点
- 结合DDE资金流向确认
- 使用session_state防止无限重载

Author: iFlow CLI
Version: V19.0
"""

import streamlit as st
import pandas as pd
from logic.midway_strategy import MidwayStrategy
from logic.logger import get_logger

logger = get_logger(__name__)

@st.cache_resource
def get_midway_strategy_instance():
    """获取半路战法实例（懒加载）"""
    return MidwayStrategy()


def render_midway_strategy_tab(db, config):
    """
    渲染半路战法标签页
    
    Args:
        db: 数据库实例
        config: 配置对象
    """
    st.markdown("## 🚀 20cm 半路逼空战法 (Midway Acceleration)")
    st.info("💡 专攻创业板/科创板：捕捉分时均线支撑后的二次加速点，结合DDE资金流向确认")
    st.markdown("---")
    
    # 1. 初始化 Session State (防止无限重跑)
    if 'midway_results' not in st.session_state:
        st.session_state.midway_results = None
        st.session_state.midway_last_scan = None
        st.session_state.midway_scan_params = {}
    
    # 2. 控制区
    with st.expander("⚙️ 策略配置", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            stock_limit = st.slider(
                "扫描股票数量",
                min_value=10,
                max_value=100,
                value=50,
                step=10,
                help="按成交量排序选择前N只最活跃的20cm股票进行扫描"
            )
            
            min_change_pct = st.slider(
                "最小涨幅 (%)",
                1.0, 10.0, 3.0,
                step=0.5,
                help="只扫描涨幅大于此值的股票"
            )
        
        with col2:
            max_change_pct = st.slider(
                "最大涨幅 (%)",
                5.0, 20.0, 12.0,
                step=0.5,
                help="避免追高，只扫描涨幅小于此值的股票"
            )
            
            min_score = st.slider(
                "信号强度阈值",
                0.0, 1.0, 0.6,
                step=0.1,
                help="信号强度低于此值将被过滤"
            )
        
        with col3:
            risk_tolerance = st.selectbox(
                "风险容忍度",
                ["低", "中", "高"],
                help="选择可接受的风险等级"
            )

            only_20cm = st.checkbox(
                "只扫描20cm标的",
                value=False,
                help="只扫描创业板(300)和科创板(688)的20cm股票，不勾选则包含主板10cm股票"
            )

            auto_refresh = st.checkbox(
                "自动刷新 (5分钟)",
                value=False,
                help="每5分钟自动重新扫描（已禁用以避免卡顿）"
            )
    
    # 3. 扫描按钮区
    col_scan1, col_scan2 = st.columns([1, 3])
    
    with col_scan1:
        # 只有点击按钮才触发
        if st.button("🔥 启动全市场扫描", use_container_width=True, key="scan_midway_v19"):
            try:
                # 保存扫描参数
                scan_params = {
                    'stock_limit': stock_limit,
                    'min_change_pct': min_change_pct,
                    'max_change_pct': max_change_pct,
                    'min_score': min_score,
                    'risk_tolerance': risk_tolerance,
                    'only_20cm': only_20cm
                }

                # 显示进度条，而不是让界面卡死
                scan_target = "20cm标的" if only_20cm else "全市场股票（包含主板）"
                with st.spinner(f"🚀 [半路战法] 正在通过 DDE 显微镜扫描 {scan_target}... 请勿刷新页面"):
                    # 🚀 V19 优化：使用懒加载函数获取策略实例
                    strategy = get_midway_strategy_instance()

                    # 执行核心逻辑
                    results = strategy.scan_market(
                        min_change_pct=min_change_pct,
                        max_change_pct=max_change_pct,
                        min_score=min_score,
                        stock_limit=stock_limit,
                        only_20cm=only_20cm
                    )
                    
                    # 过滤风险等级
                    if risk_tolerance == "低":
                        results = [r for r in results if r.get('risk_level') == '低']
                    elif risk_tolerance == "中":
                        results = [r for r in results if r.get('risk_level') != '高']
                    
                    # 存入缓存
                    st.session_state.midway_results = results
                    st.session_state.midway_last_scan = pd.Timestamp.now()
                    st.session_state.midway_scan_params = scan_params
                
                if results:
                    st.success(f"✅ 扫描完成！捕获 {len(results)} 只潜在标的")
                else:
                    st.warning("⚠️ 扫描完成，但今日无符合【20cm加速 + DDE共振】的标的")
                
                st.rerun()  # 强制刷新以显示结果
            
            except Exception as e:
                st.error(f"❌ 扫描崩溃: {str(e)}")
                logger.error(f"[半路战法] 扫描失败: {e}")
                import traceback
                st.error(traceback.format_exc())
    
    # 4. 显示上次扫描时间
    if st.session_state.midway_last_scan:
        time_diff = pd.Timestamp.now() - st.session_state.midway_last_scan
        st.caption(f"🕒 上次扫描时间: {st.session_state.midway_last_scan.strftime('%H:%M:%S')} ({time_diff.seconds // 60}分钟前)")
    
    # 5. 展示区 (只从缓存读取)
    if st.session_state.midway_results is not None:
        results = st.session_state.midway_results
        
        if results:
            st.markdown("### 🎯 捕获目标池")
            
            # 转换为DataFrame
            df = pd.DataFrame(results)
            
            # 格式化显示
            display_df = df.copy()
            display_df['score'] = display_df['score'].apply(lambda x: f"{x:.2f}")
            display_df['current_price'] = display_df['current_price'].apply(lambda x: f"¥{x:.2f}")
            display_df['dde_net'] = display_df['dde_net'].apply(lambda x: f"{x/10000:.1f}万" if x > 0 else f"{x/10000:.1f}万")
            display_df['stop_loss'] = display_df['stop_loss'].apply(lambda x: f"¥{x:.2f}")
            display_df['target_price'] = display_df['target_price'].apply(lambda x: f"¥{x:.2f}")
            
            # 重命名列
            display_df = display_df.rename(columns={
                'code': '代码',
                'name': '名称',
                'score': '信号强度',
                'reason': '入选理由',
                'current_price': '当前价',
                'dde_net': 'DDE净流入',
                'signal_type': '信号类型',
                'stop_loss': '止损价',
                'target_price': '目标价',
                'risk_level': '风险等级',
                'confidence': '置信度'
            })
            
            # 选择要显示的列
            display_cols = ['代码', '名称', '信号强度', '信号类型', '当前价', 'DDE净流入', '风险等级', '置信度']
            display_df = display_df[display_cols]
            
            # 显示数据表格
            st.dataframe(
                display_df,
                use_container_width=True,
                height=400
            )
            
            # 详细理由透视
            st.markdown("### 📋 详细分析")
            
            for idx, row in df.iterrows():
                with st.expander(f"{row['name']} ({row['code']}) - 信号强度: {row['score']:.2f} - {row['signal_type']}"):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("当前价", f"¥{row['current_price']:.2f}")
                    with col_b:
                        st.metric("止损价", f"¥{row['stop_loss']:.2f}")
                    with col_c:
                        st.metric("目标价", f"¥{row['target_price']:.2f}")
                    
                    col_d, col_e = st.columns(2)
                    with col_d:
                        st.metric("风险等级", row['risk_level'])
                    with col_e:
                        st.metric("置信度", f"{row['confidence']:.2f}")
                    
                    st.write(f"**入选理由:**")
                    st.write(row['reason'])
                    
                    st.metric("DDE 净流入", f"{row['dde_net']/10000:.1f} 万")
                    
                    # 显示技术指标
                    if 'technical_indicators' in row:
                        st.write("**技术指标:**")
                        tech_indicators = row['technical_indicators']
                        for key, value in tech_indicators.items():
                            st.write(f"- {key}: {value:.2f}")
        else:
            st.warning("⚠️ 扫描完成，但今日无符合【20cm加速 + DDE共振】的标的。建议空仓休息。")
    
    # 6. 侧边栏 - 战术说明
    with st.sidebar:
        st.markdown("---")
        st.subheader("📖 战术要点")
        
        st.info("""
        **入场条件**：
        - 创业板(300)或科创板(688)标的
        - 涨幅在3%-12%之间（避免追高）
        - 分时均线支撑确认
        - 成交量萎缩后放大
        - DDE资金净流入
        """)
        
        st.markdown("---")
        st.subheader("⚠️ 风险提醒")
        
        st.warning("""
        1. 20cm标的波动大，严格止损
        2. 市场趋势变化时及时退出
        3. 消息面影响较大
        4. 不要满仓操作
        """)
        
        st.markdown("---")
        st.subheader("📈 成功要素")
        
        st.success("""
        1. 精准的支撑位判断
        2. 量价关系确认
        3. DDE资金流向配合
        4. 风险控制严格
        """)
        
        st.markdown("---")
        st.subheader("🎯 四大核心模式")
        
        st.markdown("""
        1. **平台突破**：突破窄幅震荡平台（胜率最高）
        2. **上影线反包**：长上影线后的反包
        3. **阴线反包**：缩量阴线后的放量反包
        4. **涨停加一阳**：涨停后的空中加油
        """)