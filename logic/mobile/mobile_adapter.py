"""
移动端适配模块
提供移动端优化功能
"""

import streamlit as st


class MobileAdapter:
    """移动端适配器"""

    @staticmethod
    def is_mobile():
        """检测是否为移动端"""
        # 通过检测屏幕宽度判断
        return st.session_state.get('is_mobile', False)

    @staticmethod
    def get_layout_config():
        """获取移动端布局配置"""
        if MobileAdapter.is_mobile():
            return {
                'columns': 1,  # 移动端只显示1列
                'chart_height': 300,  # 图表高度较小
                'font_size': 12,  # 字体较小
                'show_sidebar': False  # 隐藏侧边栏
            }
        else:
            return {
                'columns': 2,  # 桌面端显示2-3列
                'chart_height': 500,  # 图表高度正常
                'font_size': 14,  # 字体正常
                'show_sidebar': True  # 显示侧边栏
            }

    @staticmethod
    def create_responsive_columns(num_columns):
        """
        创建响应式列
        
        Args:
            num_columns: 桌面端列数
        """
        if MobileAdapter.is_mobile():
            return st.columns(1)
        else:
            return st.columns(num_columns)

    @staticmethod
    def adjust_chart_height(base_height):
        """
        调整图表高度
        
        Args:
            base_height: 基础高度
        """
        if MobileAdapter.is_mobile():
            return int(base_height * 0.6)
        else:
            return base_height

    @staticmethod
    def create_mobile_friendly_button(label, key, icon=True):
        """
        创建移动端友好的按钮
        
        Args:
            label: 按钮标签
            key: 按钮key
            icon: 是否显示图标
        """
        if MobileAdapter.is_mobile():
            # 移动端按钮更大
            return st.button(label, key=key, use_container_width=True)
        else:
            return st.button(label, key=key)

    @staticmethod
    def create_mobile_friendly_input(label, key, default_value, input_type="text"):
        """
        创建移动端友好的输入框
        
        Args:
            label: 标签
            key: key
            default_value: 默认值
            input_type: 输入类型
        """
        if MobileAdapter.is_mobile():
            # 移动端输入框更大
            if input_type == "number":
                return st.number_input(label, value=default_value, key=key)
            elif input_type == "slider":
                return st.slider(label, key=key)
            else:
                return st.text_input(label, value=default_value, key=key)
        else:
            if input_type == "number":
                return st.number_input(label, value=default_value, key=key)
            elif input_type == "slider":
                return st.slider(label, key=key)
            else:
                return st.text_input(label, value=default_value, key=key)

    @staticmethod
    def optimize_for_mobile():
        """优化移动端显示"""
        if MobileAdapter.is_mobile():
            # 隐藏一些不必要的元素
            st.markdown("""
            <style>
            .stSidebar { display: none; }
            .stAppHeader { display: none; }
            </style>
            """, unsafe_allow_html=True)

            # 添加移动端提示
            st.info("📱 移动端模式已启用")

    @staticmethod
    def create_mobile_nav_menu():
        """创建移动端导航菜单"""
        if MobileAdapter.is_mobile():
            # 创建底部导航
            st.markdown("""
            <style>
            .mobile-nav {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: #f0f2f6;
                padding: 10px;
                display: flex;
                justify-content: space-around;
                z-index: 999;
            }
            </style>
            """, unsafe_allow_html=True)

            # 创建导航按钮
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                if st.button("📊", key="nav_single"):
                    st.session_state.active_tab = 0
            with col2:
                if st.button("🔍", key="nav_compare"):
                    st.session_state.active_tab = 1
            with col3:
                if st.button("🎯", key="nav_smart"):
                    st.session_state.active_tab = 15
            with col4:
                if st.button("⚠️", key="nav_risk"):
                    st.session_state.active_tab = 16
            with col5:
                if st.button("⚙️", key="nav_settings"):
                    st.session_state.active_tab = 18

    @staticmethod
    def create_mobile_quick_actions():
        """创建移动端快捷操作"""
        if MobileAdapter.is_mobile():
            st.subheader("🚀 快捷操作")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 单股分析", key="quick_single"):
                    st.session_state.active_tab = 0
                    st.rerun()
            with col2:
                if st.button("🎯 智能推荐", key="quick_smart"):
                    st.session_state.active_tab = 15
                    st.rerun()

            col1, col2 = st.columns(2)
            with col1:
                if st.button("⚠️ 风险管理", key="quick_risk"):
                    st.session_state.active_tab = 16
                    st.rerun()
            with col2:
                if st.button("📜 历史记录", key="quick_history"):
                    st.session_state.active_tab = 17
                    st.rerun()