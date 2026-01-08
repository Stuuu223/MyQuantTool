# --- 按功能大类渲染（Lazy Rendering）---
elif app_mode == "市场分析":
    # 市场分析模块 - 包含各种分析工具
    t1, t2, t3, t4, t5, t6 = st.tabs(["单股分析", "多股比较", "板块轮动", "板块强度", "情绪分析", "热点追踪"])
    with t1:
        render_single_stock_tab(db, config)
    with t2:
        render_multi_compare_tab(db, config)
    with t3:
        render_sector_rotation_tab(db, config)
    with t4:
        # 延迟导入板块强度排行模块
        with st.spinner("正在加载板块强度排行引擎..."):
            from ui.sector_strength_tab import render_sector_strength_tab
            render_sector_strength_tab(db, config)
    with t5:
        render_sentiment_tab(db, config)
    with t6:
        render_hot_topics_tab(db, config)