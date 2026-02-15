"""
标签页管理模块
提供标签页分组、搜索、快捷键等功能
"""

import streamlit as st


class TabManager:
    """标签页管理器"""

    # 标签页配置
    TAB_CONFIG = {
        # 分析类
        'analysis': {
            'name': '📊 分析工具',
            'tabs': [
                {'id': 'single', 'name': '📊 单股分析', 'hot': True},
                {'id': 'compare', 'name': '🔍 多股对比', 'hot': True},
                {'id': 'backtest', 'name': '🧪 策略回测', 'hot': False},
                {'id': 'sector', 'name': '🔄 板块轮动', 'hot': False},
            ]
        },
        # 战法类
        'strategy': {
            'name': '🎯 战法工具',
            'tabs': [
                {'id': 'lhb', 'name': '🏆 龙虎榜', 'hot': True},
                {'id': 'dragon', 'name': '🔥 龙头战法', 'hot': True},
                {'id': 'auction', 'name': '⚡ 集合竞价', 'hot': True},
                {'id': 'sentiment', 'name': '📈 情绪分析', 'hot': False},
                {'id': 'hot_topics', 'name': '🎯 热点题材', 'hot': True},
                {'id': 'vp', 'name': '📊 量价关系', 'hot': False},
                {'id': 'ma', 'name': '📈 均线战法', 'hot': False},
                {'id': 'new_stock', 'name': '🆕 次新股', 'hot': False},
                {'id': 'capital', 'name': '💰 游资席位', 'hot': False},
                {'id': 'limit_up', 'name': '🎯 打板预测', 'hot': False},
            ]
        },
        # 管理类
        'management': {
            'name': '⚙️ 管理工具',
            'tabs': [
                {'id': 'smart', 'name': '🤖 智能推荐', 'hot': True},
                {'id': 'risk', 'name': '⚠️ 风险管理', 'hot': True},
                {'id': 'history', 'name': '📜 历史记录', 'hot': False},
                {'id': 'settings', 'name': '⚙️ 系统设置', 'hot': False},
            ]
        }
    }

    # 快捷键映射
    SHORTCUT_KEYS = {
        '1': 'single',
        '2': 'compare',
        '3': 'lhb',
        '4': 'dragon',
        '5': 'auction',
        '6': 'hot_topics',
        '7': 'smart',
        '8': 'risk',
    }

    @staticmethod
    def get_all_tabs():
        """获取所有标签页"""
        all_tabs = []
        for category, config in TabManager.TAB_CONFIG.items():
            for tab in config['tabs']:
                all_tabs.append({
                    **tab,
                    'category': category,
                    'category_name': config['name']
                })
        return all_tabs

    @staticmethod
    def get_hot_tabs():
        """获取常用标签（标记为hot的）"""
        all_tabs = TabManager.get_all_tabs()
        return [tab for tab in all_tabs if tab['hot']]

    @staticmethod
    def search_tabs(keyword):
        """搜索标签页"""
        all_tabs = TabManager.get_all_tabs()
        keyword = keyword.lower()
        
        return [
            tab for tab in all_tabs
            if keyword in tab['name'].lower() or keyword in tab['id']
        ]

    @staticmethod
    def get_tabs_by_group(group_name):
        """按分组获取标签页"""
        if group_name in TabManager.TAB_CONFIG:
            return TabManager.TAB_CONFIG[group_name]['tabs']
        return []

    @staticmethod
    def get_tab_by_id(tab_id):
        """根据ID获取标签页"""
        all_tabs = TabManager.get_all_tabs()
        for tab in all_tabs:
            if tab['id'] == tab_id:
                return tab
        return None

    @staticmethod
    def render_group_selector():
        """渲染分组选择器"""
        groups = [
            {'id': 'all', 'name': '📋 全部'},
            {'id': 'hot', 'name': '⭐ 常用'},
            {'id': 'analysis', 'name': '📊 分析类'},
            {'id': 'strategy', 'name': '🎯 战法类'},
            {'id': 'management', 'name': '⚙️ 管理类'},
        ]
        
        group_names = [g['name'] for g in groups]
        selected = st.selectbox(
            "选择功能分组",
            group_names,
            index=0,
            key="tab_group_selector",
            label_visibility="collapsed"
        )
        
        selected_id = next(g['id'] for g in groups if g['name'] == selected)
        return selected_id

    @staticmethod
    def render_search_box():
        """渲染搜索框"""
        return st.text_input(
            "🔍 搜索功能",
            placeholder="输入关键词搜索...",
            key="tab_search_box"
        )

    @staticmethod
    def render_shortcut_hint():
        """渲染快捷键提示"""
        st.markdown("""
        <style>
        .shortcut-hint {
            font-size: 12px;
            color: #666;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 5px;
            margin: 10px 0;
        }
        </style>
        <div class="shortcut-hint">
            <b>快捷键：</b><br>
            1-单股分析 | 2-多股对比 | 3-龙虎榜 | 4-龙头战法<br>
            5-集合竞价 | 6-热点题材 | 7-智能推荐 | 8-风险管理
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def get_display_tabs(group_id='all', search_keyword=''):
        """获取要显示的标签页列表"""
        if search_keyword:
            # 搜索模式
            return TabManager.search_tabs(search_keyword)
        elif group_id == 'all':
            # 全部模式
            return TabManager.get_all_tabs()
        elif group_id == 'hot':
            # 常用模式
            return TabManager.get_hot_tabs()
        else:
            # 分组模式
            tabs = TabManager.get_tabs_by_group(group_id)
            # 添加分组信息
            category_name = TabManager.TAB_CONFIG.get(group_id, {}).get('name', '')
            return [
                {**tab, 'category_name': category_name}
                for tab in tabs
            ]

    @staticmethod
    def save_favorite_tabs(tab_ids):
        """保存收藏的标签页"""
        st.session_state['favorite_tabs'] = tab_ids

    @staticmethod
    def get_favorite_tabs():
        """获取收藏的标签页"""
        return st.session_state.get('favorite_tabs', [])

    @staticmethod
    def is_favorite(tab_id):
        """检查标签页是否被收藏"""
        favorites = TabManager.get_favorite_tabs()
        return tab_id in favorites

    @staticmethod
    def toggle_favorite(tab_id):
        """切换收藏状态"""
        favorites = TabManager.get_favorite_tabs()
        if tab_id in favorites:
            favorites.remove(tab_id)
        else:
            favorites.append(tab_id)
        TabManager.save_favorite_tabs(favorites)
        return tab_id in favorites

    @staticmethod
    def render_favorites_bar():
        """渲染收藏栏"""
        favorites = TabManager.get_favorite_tabs()
        
        if not favorites:
            return None
        
        st.markdown("### ⭐ 收藏的功能")
        cols = st.columns(len(favorites))
        
        for idx, tab_id in enumerate(favorites):
            tab = TabManager.get_tab_by_id(tab_id)
            if tab:
                with cols[idx]:
                    if st.button(tab['name'], key=f"fav_{tab_id}", use_container_width=True):
                        st.session_state['selected_tab'] = tab_id
                        st.rerun()

    @staticmethod
    def handle_shortcut(key):
        """处理快捷键"""
        if key in TabManager.SHORTCUT_KEYS:
            tab_id = TabManager.SHORTCUT_KEYS[key]
            st.session_state['selected_tab'] = tab_id
            return True
        return False

    @staticmethod
    def get_tab_id_by_name(tab_name):
        """根据名称获取标签ID"""
        all_tabs = TabManager.get_all_tabs()
        for tab in all_tabs:
            if tab['name'] == tab_name:
                return tab['id']
        return None

    @staticmethod
    def get_statistics():
        """获取标签页统计信息"""
        all_tabs = TabManager.get_all_tabs()
        hot_tabs = TabManager.get_hot_tabs()
        favorites = TabManager.get_favorite_tabs()
        
        return {
            'total_tabs': len(all_tabs),
            'hot_tabs': len(hot_tabs),
            'favorite_tabs': len(favorites),
            'categories': len(TabManager.TAB_CONFIG)
        }

    @staticmethod
    def render_tab_statistics():
        """渲染标签页统计信息"""
        stats = TabManager.get_statistics()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总标签数", stats['total_tabs'])
        with col2:
            st.metric("常用标签", stats['hot_tabs'])
        with col3:
            st.metric("收藏标签", stats['favorite_tabs'])
        with col4:
            st.metric("功能分组", stats['categories'])