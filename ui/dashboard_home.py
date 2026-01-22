"""
仪表盘首页 - 展示系统健康状态和数据记录情况
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path

from logic.database_manager import DatabaseManager
from logic.logger import get_logger
from logic.auction_snapshot_manager import AuctionSnapshotManager

logger = get_logger(__name__)


def render_dashboard_home():
    """渲染仪表盘首页"""

    st.set_page_config(
        page_title="量化工具 - 仪表盘",
        page_icon="📊",
        layout="wide"
    )

    st.title("📊 系统仪表盘")
    st.caption("实时监控系统健康状态和数据记录情况")
    st.markdown("---")

    # 数据库和Redis状态检查
    if 'dashboard_db' not in st.session_state:
        # 加载数据库配置
        import json
        config_path = Path(__file__).parent.parent / 'config_database.json'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                db_config = json.load(f)
        else:
            db_config = {}
        st.session_state.dashboard_db = DatabaseManager(db_config)

    db = st.session_state.dashboard_db

    # 自动刷新
    col_refresh1, col_refresh2 = st.columns([1, 1])
    with col_refresh1:
        auto_refresh = st.checkbox("自动刷新（每30秒）", value=False, key="dashboard_auto_refresh")
    with col_refresh2:
        if st.button("🔄 立即刷新", key="dashboard_refresh"):
            st.rerun()

    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()

    st.markdown("---")

    # 第一行：服务状态概览
    st.subheader("🔌 服务状态概览")
    col1, col2, col3, col4 = st.columns(4)

    # Redis状态
    with col1:
        redis_status = check_redis_status(db)
        if redis_status['status'] == 'online':
            st.success(f"🟢 Redis: {redis_status['status']}")
            st.metric("连接数", redis_stats.get('connected_clients', 0))
            st.metric("键数量", redis_stats.get('key_count', 0))
        else:
            st.error(f"🔴 Redis: {redis_status['status']}")
            st.warning(f"错误: {redis_status.get('error', '未知错误')}")

    # SQLite状态
    with col2:
        sqlite_status = check_sqlite_status(db)
        if sqlite_status['status'] == 'online':
            st.success(f"🟢 SQLite: {sqlite_status['status']}")
            st.metric("表数量", sqlite_status.get('table_count', 0))
            st.metric("总记录数", sqlite_status.get('total_records', 0))
        else:
            st.error(f"🔴 SQLite: {sqlite_status['status']}")
            st.warning(f"错误: {sqlite_status.get('error', '未知错误')}")

    # 数据健康度
    with col3:
        health_score = calculate_data_health(db)
        health_color = "🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"
        st.metric(f"{health_color} 数据健康度", f"{health_score}/100")

    # 系统运行时间
    with col4:
        uptime = get_system_uptime()
        st.metric("⏱️ 系统运行时间", uptime)

    st.markdown("---")

    # 第二行：竞价快照管理
    st.subheader("⚡ 竞价快照管理")

    auction_status = check_auction_snapshot_status(db)

    col_auction1, col_auction2, col_auction3, col_auction4 = st.columns(4)

    with col_auction1:
        if auction_status['is_available']:
            st.success(f"🟢 竞价快照: 可用")
        else:
            st.error(f"🔴 竞价快照: 不可用")
            if 'error' in auction_status:
                st.warning(f"错误: {auction_status['error']}")

    with col_auction2:
        if auction_status['is_auction_time']:
            st.info(f"🕐 当前时间: 竞价时段")
        elif auction_status['is_after_market_open']:
            st.success(f"🕐 当前时间: 开盘后")
        else:
            st.info(f"🕐 当前时间: 非交易时段")

    with col_auction3:
        if auction_status['is_available']:
            st.metric("今日快照数", auction_status.get('snapshot_count', 0))
        else:
            st.metric("今日快照数", "N/A")

    with col_auction4:
        st.metric("日期", auction_status.get('today', 'N/A'))

    # 显示最近快照示例
    if auction_status.get('recent_snapshots'):
        st.markdown("### 📋 最近竞价快照（前5条）")
        snapshot_df = pd.DataFrame(auction_status['recent_snapshots'])
        snapshot_df['竞价量(手)'] = snapshot_df['auction_volume'].apply(lambda x: f"{x:,.0f}")
        snapshot_df['竞价金额(元)'] = snapshot_df['auction_amount'].apply(lambda x: f"{x:,.0f}")
        snapshot_df['快照时间'] = pd.to_datetime(snapshot_df['snapshot_time'], unit='s').dt.strftime('%H:%M:%S')
        snapshot_df = snapshot_df[['stock_code', '竞价量(手)', '竞价金额(元)', '快照时间']]
        snapshot_df.columns = ['股票代码', '竞价量(手)', '竞价金额(元)', '快照时间']
        st.dataframe(snapshot_df, use_container_width=True)
    elif auction_status['is_available']:
        st.info("📭 今日暂无竞价快照数据")
    else:
        st.warning("⚠️ 竞价快照功能不可用，请检查 Redis 连接")

    st.markdown("---")

    # 第三行：数据记录情况
    st.subheader("📈 数据记录情况")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        # 数据记录趋势图
        st.markdown("### 📊 数据记录趋势（近7天）")
        trend_data = get_data_record_trend(db)
        if trend_data:
            fig = px.line(
                trend_data,
                x='date',
                y='record_count',
                title='每日数据记录数量',
                markers=True
            )
            fig.update_layout(
                xaxis_title='日期',
                yaxis_title='记录数量',
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("暂无数据记录趋势")

    with col_right:
        # 数据记录分布
        st.markdown("### 📊 数据记录分布")
        distribution = get_data_distribution(db)
        if distribution:
            fig = px.pie(
                distribution,
                values='count',
                names='table',
                title='各表数据分布'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("暂无数据分布信息")

    st.markdown("---")

    # 第四行：数据问题诊断
    st.subheader("🔍 数据问题诊断")

    col_diag1, col_diag2 = st.columns([1, 1])

    with col_diag1:
        st.markdown("### ⚠️ 数据缺失天数")
        missing_days = find_missing_data_days(db)
        if missing_days:
            st.warning(f"发现 {len(missing_days)} 天数据缺失")
            missing_df = pd.DataFrame({
                '日期': missing_days,
                '状态': ['缺失'] * len(missing_days)
            })
            st.dataframe(missing_df, use_container_width=True)
        else:
            st.success("✅ 近7天数据完整，无缺失")

    with col_diag2:
        st.markdown("### 📝 数据质量报告")
        quality_report = generate_quality_report(db)
        if quality_report:
            for item in quality_report:
                if item['status'] == 'ok':
                    st.success(f"✅ {item['name']}: {item['message']}")
                elif item['status'] == 'warning':
                    st.warning(f"⚠️ {item['name']}: {item['message']}")
                else:
                    st.error(f"❌ {item['name']}: {item['message']}")
        else:
            st.info("暂无质量报告")

    st.markdown("---")

    # 第四行：Redis数据详情
    st.subheader("💾 Redis数据详情")

    col_redis1, col_redis2 = st.columns([1, 1])

    with col_redis1:
        st.markdown("### 📊 Redis键分布")
        redis_keys_info = get_redis_keys_info(db)
        if redis_keys_info:
            keys_df = pd.DataFrame(redis_keys_info)
            st.dataframe(keys_df, use_container_width=True)
        else:
            st.info("Redis中暂无数据")

    with col_redis2:
        st.markdown("### 📈 Redis键过期情况")
        expiration_info = get_redis_expiration_info(db)
        if expiration_info:
            exp_df = pd.DataFrame(expiration_info)
            st.dataframe(exp_df, use_container_width=True)
        else:
            st.info("暂无过期信息")

    st.markdown("---")

    # 第五行：服务性能监控
    st.subheader("⚡ 服务性能监控")

    col_perf1, col_perf2, col_perf3 = st.columns(3)

    with col_perf1:
        st.metric("🚀 Redis响应时间", f"{redis_status.get('response_time', 0):.2f}ms")

    with col_perf2:
        st.metric("🚀 SQLite响应时间", f"{sqlite_status.get('response_time', 0):.2f}ms")

    with col_perf3:
        st.metric("💾 磁盘使用", f"{get_disk_usage():.1f}%")

    st.markdown("---")

    # 第六行：日志摘要
    st.subheader("📜 日志摘要")

    col_log1, col_log2 = st.columns([1, 1])

    with col_log1:
        st.markdown("### 🔴 错误日志（最近10条）")
        error_logs = get_recent_logs(level='ERROR', limit=10)
        if error_logs:
            for log in error_logs:
                st.error(f"{log['time']}: {log['message']}")
        else:
            st.success("✅ 最近无错误日志")

    with col_log2:
        st.markdown("### ⚠️ 警告日志（最近10条）")
        warning_logs = get_recent_logs(level='WARNING', limit=10)
        if warning_logs:
            for log in warning_logs:
                st.warning(f"{log['time']}: {log['message']}")
        else:
            st.success("✅ 最近无警告日志")


def check_redis_status(db):
    """检查Redis状态（懒加载模式）"""
    import time
    start_time = time.time()

    try:
        # 尝试初始化Redis连接（如果尚未初始化）
        if not db._redis_initialized:
            db._init_redis()
            db._redis_initialized = True

        # 检查Redis客户端是否可用
        if db._redis_client:
            db._redis_client.ping()
            response_time = (time.time() - start_time) * 1000

            # 获取Redis统计信息
            global redis_stats
            redis_stats = {
                'connected_clients': db._redis_client.client_list().__len__() if hasattr(db._redis_client, 'client_list') else 1,
                'key_count': db._redis_client.dbsize(),
                'used_memory': db._redis_client.info().get('used_memory_human', '0B'),
                'uptime': db._redis_client.info().get('uptime_in_days', 0)
            }

            return {
                'status': 'online',
                'response_time': response_time,
                'stats': redis_stats
            }
        else:
            return {
                'status': 'offline',
                'error': 'Redis服务未运行或连接失败'
            }
    except Exception as e:
        return {
            'status': 'offline',
            'error': str(e)
        }


def check_sqlite_status(db):
    """检查SQLite状态"""
    import time
    start_time = time.time()

    try:
        cursor = db.conn.cursor()

        # 获取表数量
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        # 获取总记录数
        total_records = 0
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            total_records += cursor.fetchone()[0]

        response_time = (time.time() - start_time) * 1000

        return {
            'status': 'online',
            'response_time': response_time,
            'table_count': len(tables),
            'total_records': total_records
        }
    except Exception as e:
        return {
            'status': 'offline',
            'error': str(e)
        }


def calculate_data_health(db):
    """计算数据健康度"""
    try:
        # 基础分：100分
        health_score = 100

        # 检查Redis
        if not check_redis_status(db)['status'] == 'online':
            health_score -= 20

        # 检查SQLite
        if not check_sqlite_status(db)['status'] == 'online':
            health_score -= 30

        # 检查数据完整性
        missing_days = find_missing_data_days(db)
        if missing_days:
            health_score -= len(missing_days) * 5

        # 检查最近错误日志
        error_logs = get_recent_logs(level='ERROR', limit=1)
        if error_logs:
            health_score -= 10

        return max(0, health_score)
    except Exception as e:
        logger.error(f"计算数据健康度失败: {e}")
        return 0


def get_system_uptime():
    """获取系统运行时间"""
    try:
        # 优先使用psutil（跨平台）
        try:
            import psutil
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time

            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            return f"{days}天 {hours}小时 {minutes}分钟"
        except ImportError:
            pass

        # Windows系统：使用systeminfo命令
        try:
            import subprocess
            import re
            result = subprocess.run(['systeminfo'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # 查找系统启动时间
                match = re.search(r'系统启动时间:\s*(.+)', result.stdout)
                if match:
                    boot_time_str = match.group(1).strip()
                    # 尝试解析启动时间
                    try:
                        # Windows中文系统格式：2026/1/21, 9:00:00
                        boot_time = datetime.strptime(boot_time_str, '%Y/%m/%d, %H:%M:%S')
                    except:
                        # 尝试其他格式
                        boot_time = datetime.strptime(boot_time_str.split(',')[0], '%Y/%m/%d')

                    uptime = datetime.now() - boot_time
                    days = uptime.days
                    hours, remainder = divmod(uptime.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)

                    return f"{days}天 {hours}小时 {minutes}分钟"
        except:
            pass

        # 如果都失败，返回应用运行时间
        from time import time
        if 'app_start_time' not in st.session_state:
            st.session_state.app_start_time = time()

        app_uptime = time() - st.session_state.app_start_time
        hours, remainder = divmod(int(app_uptime), 3600)
        minutes, _ = divmod(remainder, 60)

        return f"{hours}小时 {minutes}分钟（应用运行时间）"

    except:
        return "未知"


def check_auction_snapshot_status(db):
    """检查竞价快照状态"""
    try:
        # 初始化竞价快照管理器
        auction_manager = AuctionSnapshotManager(db)
        status = auction_manager.get_snapshot_status()

        # 如果 Redis 可用，获取今日竞价快照数量
        if status['is_available']:
            try:
                # 扫描 Redis 中的竞价快照键
                today = status['today']
                pattern = f"auction:{today}:*"

                # 使用 Redis 的 SCAN 命令（如果可用）
                if db._redis_client:
                    # 尝试获取所有匹配的键
                    keys = db._redis_client.keys(pattern)
                    status['snapshot_count'] = len(keys)

                    # 获取前5个快照示例
                    status['recent_snapshots'] = []
                    for key in keys[:5]:
                        stock_code = key.split(':')[-1]
                        raw_data = db._redis_client.get(key)
                        if raw_data:
                            import json
                            data = json.loads(raw_data)
                            status['recent_snapshots'].append({
                                'stock_code': stock_code,
                                'auction_volume': data.get('auction_volume', 0),
                                'auction_amount': data.get('auction_amount', 0),
                                'snapshot_time': data.get('snapshot_time', 0)
                            })
            except Exception as e:
                logger.error(f"获取竞价快照统计失败: {e}")
                status['snapshot_count'] = 0
                status['recent_snapshots'] = []

        return status
    except Exception as e:
        logger.error(f"检查竞价快照状态失败: {e}")
        return {
            'is_available': False,
            'is_auction_time': False,
            'is_after_market_open': False,
            'today': datetime.now().strftime("%Y%m%d"),
            'redis_connected': False,
            'snapshot_count': 0,
            'recent_snapshots': [],
            'error': str(e)
        }


def get_data_record_trend(db):
    """获取数据记录趋势（近7天）"""
    try:
        cursor = db.conn.cursor()

        # 检查是否有daily_bars表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_bars'")
        if not cursor.fetchone():
            return []

        # 获取近7天的数据记录数量
        cursor.execute("""
            SELECT date, COUNT(*) as record_count
            FROM daily_bars
            WHERE date >= date('now', '-7 days')
            GROUP BY date
            ORDER BY date
        """)

        results = cursor.fetchall()
        if not results:
            return []

        return pd.DataFrame(results, columns=['date', 'record_count']).to_dict('records')
    except Exception as e:
        logger.error(f"获取数据记录趋势失败: {e}")
        return []


def get_data_distribution(db):
    """获取数据分布"""
    try:
        cursor = db.conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        distribution = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            distribution.append({
                'table': table_name,
                'count': count
            })

        return distribution
    except Exception as e:
        logger.error(f"获取数据分布失败: {e}")
        return []


def find_missing_data_days(db):
    """查找缺失数据的天数（近7天）"""
    try:
        cursor = db.conn.cursor()

        # 检查是否有daily_bars表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_bars'")
        if not cursor.fetchone():
            return []

        # 获取近7天的日期
        cursor.execute("""
            SELECT DISTINCT date
            FROM daily_bars
            WHERE date >= date('now', '-7 days')
            ORDER BY date
        """)

        existing_days = [row[0] for row in cursor.fetchall()]

        # 生成近7天的日期列表
        missing_days = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            if date not in existing_days:
                missing_days.append(date)

        return missing_days
    except Exception as e:
        logger.error(f"查找缺失数据天数失败: {e}")
        return []


def generate_quality_report(db):
    """生成数据质量报告"""
    report = []

    try:
        # 检查Redis
        redis_status = check_redis_status(db)
        if redis_status['status'] == 'online':
            report.append({
                'name': 'Redis连接',
                'status': 'ok',
                'message': f'连接正常，响应时间 {redis_status["response_time"]:.2f}ms'
            })
        else:
            report.append({
                'name': 'Redis连接',
                'status': 'error',
                'message': f'连接失败: {redis_status["error"]}'
            })

        # 检查SQLite
        sqlite_status = check_sqlite_status(db)
        if sqlite_status['status'] == 'online':
            report.append({
                'name': 'SQLite连接',
                'status': 'ok',
                'message': f'连接正常，{sqlite_status["table_count"]}个表，{sqlite_status["total_records"]}条记录'
            })
        else:
            report.append({
                'name': 'SQLite连接',
                'status': 'error',
                'message': f'连接失败: {sqlite_status["error"]}'
            })

        # 检查数据完整性
        missing_days = find_missing_data_days(db)
        if missing_days:
            report.append({
                'name': '数据完整性',
                'status': 'warning',
                'message': f'近7天缺失 {len(missing_days)} 天数据'
            })
        else:
            report.append({
                'name': '数据完整性',
                'status': 'ok',
                'message': '近7天数据完整'
            })

        return report
    except Exception as e:
        logger.error(f"生成质量报告失败: {e}")
        return []


def get_redis_keys_info(db):
    """获取Redis键信息"""
    try:
        if not db._redis_client:
            return []

        keys = db._redis_client.keys('*')
        if not keys:
            return []

        keys_info = []
        for key in keys[:20]:  # 只显示前20个键
            key_type = db._redis_client.type(key)
            ttl = db._redis_client.ttl(key)
            keys_info.append({
                '键名': key,
                '类型': key_type,
                'TTL': ttl if ttl > 0 else '永不过期'
            })

        return keys_info
    except Exception as e:
        logger.error(f"获取Redis键信息失败: {e}")
        return []


def get_redis_expiration_info(db):
    """获取Redis过期信息"""
    try:
        if not db._redis_client:
            return []

        keys = db._redis_client.keys('*')
        if not keys:
            return []

        expiration_info = []
        for key in keys:
            ttl = db._redis_client.ttl(key)
            if ttl > 0:
                expiration_info.append({
                    '键名': key,
                    '剩余时间(秒)': ttl,
                    '过期时间': datetime.now() + timedelta(seconds=ttl)
                })

        return expiration_info
    except Exception as e:
        logger.error(f"获取Redis过期信息失败: {e}")
        return []


def get_disk_usage():
    """获取磁盘使用率"""
    try:
        import psutil
        disk = psutil.disk_usage('/')
        return disk.percent
    except:
        return 0


def get_recent_logs(level='ERROR', limit=10):
    """获取最近的日志"""
    try:
        log_dir = Path('logs')
        if not log_dir.exists():
            return []

        # 查找最新的日志文件
        log_files = sorted(log_dir.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)
        if not log_files:
            return []

        latest_log = log_files[0]

        # 读取日志文件
        logs = []
        with open(latest_log, 'r', encoding='utf-8') as f:
            for line in f:
                if f' - {level} - ' in line:
                    try:
                        # 解析日志行
                        parts = line.split(' - ')
                        if len(parts) >= 3:
                            time_str = parts[0]
                            message = ' - '.join(parts[2:])
                            logs.append({
                                'time': time_str,
                                'message': message.strip()
                            })
                            if len(logs) >= limit:
                                break
                    except:
                        continue

        return logs
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        return []


# 初始化全局变量
redis_stats = {}