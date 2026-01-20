#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统监控UI组件

功能：
1. 显示Redis服务状态
2. 显示竞价快照状态
3. 显示定时任务状态
4. 显示告警信息
5. 控制台告警

Author: iFlow CLI
Version: V1.0
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
import streamlit as st

# 添加项目根目录到路径
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def render_system_monitor_tab():
    """渲染系统监控标签页"""
    st.header("🔍 系统监控")
    
    st.subheader("📊 系统状态概览")
    
    # 获取系统状态
    status = get_system_status()
    
    # 显示状态卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Redis服务",
            "✅ 正常" if status['redis_ok'] else "❌ 异常",
            delta_color="normal" if status['redis_ok'] else "inverse"
        )
    
    with col2:
        st.metric(
            "竞价快照",
            "✅ 正常" if status['auction_ok'] else "❌ 异常",
            delta_color="normal" if status['auction_ok'] else "inverse"
        )
    
    with col3:
        st.metric(
            "定时任务",
            "✅ 运行中" if status['scheduler_running'] else "⚠️ 未运行",
            delta_color="normal" if status['scheduler_running'] else "inverse"
        )
    
    with col4:
        st.metric(
            "告警数量",
            status['alerts_count'],
            delta_color="inverse" if status['alerts_count'] > 0 else "normal"
        )
    
    # 显示定时任务状态
    st.subheader("📅 定时任务状态")
    
    tasks = get_scheduled_tasks()
    
    for task_name, task_info in tasks.items():
        with st.expander(f"⏰ {task_info['description']} ({task_info['time']})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**状态**: {'✅ 已启用' if task_info['enabled'] else '❌ 已禁用'}")
                st.write(f"**执行时间**: {task_info['time']}")
                if 'last_run' in task_info:
                    st.write(f"**上次运行**: {task_info['last_run']}")
            
            with col2:
                if st.button(f"🔄 立即执行", key=f"run_{task_name}", use_container_width=True):
                    execute_task(task_name)
                    st.success(f"✅ {task_info['description']} 已执行")
                    st.rerun()
    
    # 显示告警信息
    st.subheader("🚨 告警信息")
    
    alerts = get_alerts(limit=20)
    
    if not alerts:
        st.info("✅ 暂无告警信息")
    else:
        # 按严重程度分组
        critical_alerts = [a for a in alerts if a['severity'] == 'CRITICAL']
        error_alerts = [a for a in alerts if a['severity'] == 'ERROR']
        warning_alerts = [a for a in alerts if a['severity'] == 'WARNING']
        info_alerts = [a for a in alerts if a['severity'] == 'INFO']
        
        # 显示严重告警
        if critical_alerts:
            st.error(f"🔴 严重告警 ({len(critical_alerts)})")
            for alert in critical_alerts:
                st.error(f"**{alert['timestamp']}**: {alert['message']}")
                if alert.get('details'):
                    st.json(alert['details'])
        
        # 显示错误告警
        if error_alerts:
            st.error(f"⛔ 错误告警 ({len(error_alerts)})")
            for alert in error_alerts:
                st.error(f"**{alert['timestamp']}**: {alert['message']}")
                if alert.get('details'):
                    st.json(alert['details'])
        
        # 显示警告告警
        if warning_alerts:
            st.warning(f"⚠️ 警告告警 ({len(warning_alerts)})")
            for alert in warning_alerts:
                st.warning(f"**{alert['timestamp']}**: {alert['message']}")
                if alert.get('details'):
                    with st.expander("查看详情"):
                        st.json(alert['details'])
        
        # 显示信息告警
        if info_alerts:
            st.info(f"ℹ️ 信息告警 ({len(info_alerts)})")
            for alert in info_alerts:
                st.info(f"**{alert['timestamp']}**: {alert['message']}")
    
    # 清除告警按钮
    if alerts and st.button("🗑️ 清除所有告警", use_container_width=True):
        clear_alerts()
        st.success("✅ 告警已清除")
        st.rerun()
    
    # 手动检查按钮
    st.subheader("🔧 手动检查")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 检查Redis", use_container_width=True):
            result = check_redis()
            if result:
                st.success("✅ Redis服务正常")
            else:
                st.error("❌ Redis服务异常")
                if st.button("🔄 尝试启动Redis", key="start_redis"):
                    start_redis()
                    st.success("✅ Redis服务已启动")
                    st.rerun()
    
    with col2:
        if st.button("🔍 检查竞价快照", use_container_width=True):
            result = check_auction_snapshot()
            if result:
                st.success("✅ 竞价快照正常")
            else:
                st.error("❌ 竞价快照异常")
    
    with col3:
        if st.button("🔍 执行早盘前检查", use_container_width=True):
            execute_pre_market_check()
            st.success("✅ 早盘前检查完成")
            st.rerun()


def get_system_status() -> Dict[str, Any]:
    """获取系统状态"""
    try:
        from logic.scheduled_task_monitor import ScheduledTaskMonitor
        monitor = ScheduledTaskMonitor()
        return monitor.get_system_status()
    except Exception as e:
        st.error(f"获取系统状态失败: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'redis_ok': False,
            'auction_ok': False,
            'alerts_count': 0,
            'recent_alerts': [],
            'scheduler_running': False
        }


def get_scheduled_tasks() -> Dict[str, Any]:
    """获取定时任务配置"""
    return {
        'pre_market_check': {
            'time': '09:10',
            'enabled': True,
            'description': '早盘前系统检查',
            'last_run': '未运行'
        },
        'post_market_review': {
            'time': '15:30',
            'enabled': True,
            'description': '收盘后复盘',
            'last_run': '未运行'
        },
        'weekly_check': {
            'time': '20:00',
            'enabled': True,
            'description': '每周系统检查',
            'last_run': '未运行'
        }
    }


def get_alerts(limit: int = 20) -> List[Dict]:
    """获取告警列表"""
    try:
        alert_file = "data/scheduled_alerts.json"
        if os.path.exists(alert_file):
            with open(alert_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data['alerts'][-limit:]
        return []
    except Exception as e:
        st.error(f"获取告警失败: {e}")
        return []


def clear_alerts():
    """清除所有告警"""
    try:
        alert_file = "data/scheduled_alerts.json"
        with open(alert_file, 'w', encoding='utf-8') as f:
            json.dump({
                'alerts': [],
                'last_check': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"清除告警失败: {e}")


def check_redis() -> bool:
    """检查Redis状态"""
    try:
        from logic.scheduled_task_monitor import ScheduledTaskMonitor
        monitor = ScheduledTaskMonitor()
        return monitor.check_redis_status()
    except Exception as e:
        st.error(f"检查Redis失败: {e}")
        return False


def start_redis() -> bool:
    """启动Redis服务"""
    try:
        from logic.scheduled_task_monitor import ScheduledTaskMonitor
        monitor = ScheduledTaskMonitor()
        return monitor.start_redis_service()
    except Exception as e:
        st.error(f"启动Redis失败: {e}")
        return False


def check_auction_snapshot() -> bool:
    """检查竞价快照"""
    try:
        from logic.scheduled_task_monitor import ScheduledTaskMonitor
        monitor = ScheduledTaskMonitor()
        return monitor.check_auction_snapshot()
    except Exception as e:
        st.error(f"检查竞价快照失败: {e}")
        return False


def execute_task(task_name: str):
    """执行指定的定时任务"""
    try:
        from logic.scheduled_task_monitor import ScheduledTaskMonitor
        monitor = ScheduledTaskMonitor()
        
        if task_name == 'pre_market_check':
            monitor.run_pre_market_check()
        elif task_name == 'post_market_review':
            monitor.run_post_market_review()
        elif task_name == 'weekly_check':
            monitor.run_weekly_check()
        else:
            st.error(f"未知的任务: {task_name}")
    except Exception as e:
        st.error(f"执行任务失败: {e}")


def execute_pre_market_check():
    """执行早盘前检查"""
    execute_task('pre_market_check')


def show_system_alerts():
    """在侧边栏显示系统告警"""
    try:
        alerts = get_alerts(limit=5)
        
        if alerts:
            with st.sidebar:
                st.subheader("🚨 系统告警")
                
                for alert in alerts:
                    if alert['severity'] == 'CRITICAL':
                        st.error(f"🔴 {alert['message']}")
                    elif alert['severity'] == 'ERROR':
                        st.error(f"⛔ {alert['message']}")
                    elif alert['severity'] == 'WARNING':
                        st.warning(f"⚠️ {alert['message']}")
                    else:
                        st.info(f"ℹ️ {alert['message']}")
                
                if st.button("查看详情", key="view_alerts"):
                    st.session_state['show_alerts'] = True
    except Exception as e:
        pass  # 静默失败，避免影响主界面


if __name__ == '__main__':
    render_system_monitor_tab()