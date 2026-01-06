"""
游资席位分析模块
分析龙虎榜游资、游资操作模式、识别知名游资"""

import pandas as pd
import sqlite3
import json
import time
from datetime import datetime, timedelta
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from logic.data_manager import DataManager


class CacheManager:
    """缓存管理器 - 使用SQLite缓存API数据"""

    def __init__(self, db_path='data/cache.db'):
        """初始化缓存管理器"""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_cache (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def get(self, key):
        """从缓存获取数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT data, expires_at FROM api_cache
            WHERE key = ? AND expires_at > CURRENT_TIMESTAMP
        ''', (key,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return json.loads(result[0])
        return None

    def set(self, key, data, ttl=3600):
        """设置缓存数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        expires_at = datetime.now() + timedelta(seconds=ttl)
        cursor.execute('''
            INSERT OR REPLACE INTO api_cache (key, data, expires_at)
            VALUES (?, ?, ?)
        ''', (key, json.dumps(data), expires_at.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()

    def clear_expired(self):
        """清理过期缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM api_cache WHERE expires_at <= CURRENT_TIMESTAMP')
        conn.commit()
        conn.close()


def retry_with_backoff(max_retries=3, backoff_factor=2):
    """
    指数退避重试装饰器

    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避因子
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        print(f"函数 {func.__name__} 重试 {max_retries} 次后仍然失败: {e}")
                        raise

                    wait_time = backoff_factor ** retries
                    print(f"函数 {func.__name__} 执行失败，{wait_time} 秒后进行第 {retries + 1} 次重试...")
                    time.sleep(wait_time)

            return None
        return wrapper
    return decorator


class CapitalAnalyzer:
    """游资席位分析模块"""

    # 知名游资席位列表（包含常见变体）
    FAMOUS_CAPITALISTS = {
        "章盟主": [
            "中信证券股份有限公司杭州延安路证券营业部",
            "国泰君安证券股份有限公司上海分公司",
            "国泰君安证券股份有限公司上海江苏路证券营业部",
            "国泰君安证券股份有限公司上海江苏",
            "中信证券杭州延安路",
            "国泰君安上海江苏路",
            "国泰君安上海分公司"
        ],
        "方新侠": [
            "兴业证券股份有限公司西安分公司",
            "中信证券股份有限公司西安朱雀大街证券营业部",
            "兴业证券西安分公司",
            "中信证券西安朱雀大街",
            "兴业证券股份有限公司"
        ],
        "徐翔": [
            "国泰君安证券股份有限公司上海福山路证券营业部",
            "光大证券股份有限公司宁波解放南路证券营业部",
            "国泰君安上海福山路",
            "光大证券宁波解放南路",
            "国泰君安上海福建路"
        ],
        "赵老哥": [
            "中国银河证券股份有限公司绍兴证券营业部",
            "华泰证券股份有限公司浙江分公司",
            "银河证券绍兴",
            "华泰证券浙江分公司",
            "中国银河证券绍兴"
        ],
        "炒股养家": [
            "中信证券股份有限公司上海淮海中路证券营业部",
            "国泰君安证券股份有限公司上海分公司",
            "中信证券上海淮海中路",
            "国泰君安上海分公司"
        ],
        "成都": [
            "华泰证券股份有限公司成都蜀金路证券营业部",
            "国泰君安证券股份有限公司成都分公司",
            "中信证券成都蜀金路",
            "国泰君安成都分公司"
        ],
        "深圳": [
            "光大证券股份有限公司深圳金田路证券营业部",
            "长江证券股份有限公司深圳科苑路证券营业部",
            "光大证券深圳金田路",
            "长江证券深圳科苑路",
            "光大证券深圳"
        ],
        "乔帮主": [
            "中国中金财富证券有限公司深圳分公司",
            "华泰证券股份有限公司深圳彩田路超算中心证券营业部",
            "中金财富深圳",
            "华泰证券深圳彩田路",
            "中国中金财富深圳"
        ],
        "作手新一": [
            "国泰君安证券股份有限公司南京太平南路证券营业部",
            "华泰证券股份有限公司南京江东中路证券营业部",
            "国泰君安南京太平南路",
            "华泰证券南京江东中路",
            "国泰君安南京"
        ],
        "小鳄鱼": [
            "中国银河证券股份有限公司北京中关村大街证券营业部",
            "中信证券股份有限公司北京总部证券营业部",
            "银河证券北京中关村大街",
            "中信证券北京总部",
            "银河证券北京"
        ],
        "拉萨帮": [
            "东方财富证券股份有限公司拉萨东环路第二证券营业部",
            "东方财富证券股份有限公司拉萨团结路第一证券营业部",
            "东方财富证券股份有限公司拉萨东环路第一证券营业部",
            "东方财富证券股份有限公司拉萨团结路第二证券营业部",
            "东方财富拉萨东环路第二",
            "东方财富拉萨团结路第一",
            "东方财富拉萨"
        ],
        "机构": [
            "深股通专用",
            "沪股通专用",
            "机构专用",
            "机构专用席位"
        ],
        "华泰": [
            "华泰证券股份有限公司南京庐山路证券营业部",
            "华泰证券股份有限公司浙江分公司",
            "华泰证券股份有限公司成都蜀金路证券营业部",
            "华泰证券股份有限公司深圳彩田路超算中心证券营业部",
            "华泰证券南京庐山路",
            "华泰证券浙江分公司",
            "华泰证券成都蜀金路",
            "华泰证券深圳彩田路"
        ],
        "国盛": [
            "国盛证券有限责任公司宁波桑田路证券营业部",
            "国盛证券宁波桑田路"
        ],
        "开源": [
            "开源证券股份有限公司西安西大街证券营业部",
            "开源证券西安西大街"
        ],
        "国信": [
            "国信证券股份有限公司浙江互联网分公司",
            "国信证券浙江互联网分公司"
        ],
        "爱建": [
            "爱建证券有限责任公司上海浦东新区前滩大道证券营业部",
            "爱建证券上海浦东新区前滩大道"
        ]
    }

    # 初始化缓存管理器
    cache = CacheManager()

    @staticmethod
    def analyze_longhubu_capital(date=None):
        """
        分析龙虎榜游资
        返回当日龙虎榜中的游资席位分析

        数据源策略（三层）：
        1. 第一层：东方财富接口 - 使用 stock_lhb_detail_em 获取龙虎榜股票，然后使用 stock_lhb_yyb_detail_em 按营业部代码查询详细数据
        2. 第二层：新浪接口 - 使用 stock_lhb_yytj_sina 获取累积统计数据
        3. 第三层：本地缓存 - 如果前两层都失败，返回历史数据
        """
        try:
            import akshare as ak
            from datetime import datetime
            import time

            # 检查缓存
            cache_key = f"lhb_capital_{date or 'latest'}"
            cached_data = CapitalAnalyzer.cache.get(cache_key)
            if cached_data:
                print(f"从缓存获取数据: {cache_key}")
                return cached_data

            # ===== 第一层：东方财富接口 =====
            print("=" * 60)
            print("第一层数据源：东方财富接口")
            print("=" * 60)

            # 获取龙虎榜数据
            try:
                if date:
                    if isinstance(date, str):
                        # 支持多种日期格式
                        if '-' in date:
                            # %Y-%m-%d 格式
                            date_obj = pd.to_datetime(date)
                            date_str = date_obj.strftime("%Y%m%d")
                        else:
                            date_str = date
                    else:
                        date_str = date.strftime("%Y%m%d")
                    lhb_df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)
                    print(f"获取 {date_str} 的龙虎榜数据，共 {len(lhb_df)} 条记录")
                else:
                    # 获取最近几天的数据
                    today = datetime.now()
                    lhb_df = ak.stock_lhb_detail_em(start_date=today.strftime("%Y%m%d"), end_date=today.strftime("%Y%m%d"))
                    print(f"获取今日龙虎榜数据，共 {len(lhb_df)} 条记录")

                    # 如果今日无数据，尝试获取昨天
                    if lhb_df.empty:
                        yesterday = today - pd.Timedelta(days=1)
                        lhb_df = ak.stock_lhb_detail_em(start_date=yesterday.strftime("%Y%m%d"), end_date=yesterday.strftime("%Y%m%d"))
                        print(f"今日无数据，获取昨日龙虎榜数据，共 {len(lhb_df)} 条记录")
            except Exception as e:
                print(f"获取龙虎榜数据失败: {e}")
                lhb_df = None

            # 如果龙虎榜数据为空，尝试第二层数据源
            if lhb_df is None or lhb_df.empty:
                print("龙虎榜数据为空，切换到第二层数据源")
                return CapitalAnalyzer._get_sina_data()

            print(f"[OK] 获取 {len(lhb_df)} 只龙虎榜股票")

            # ===== 方案1：按股票逐个查询营业部明细（并发优化） =====
            print("=" * 60)
            print("方案1：按股票逐个查询营业部明细（并发查询）")
            print("=" * 60)

            # 使用并发查询获取营业部明细
            seat_detail_result = CapitalAnalyzer._get_seat_detail_by_stock_concurrent(lhb_df, date_str)
            if seat_detail_result is not None:
                return seat_detail_result

            # 如果并发查询失败，切换到第二层数据源
            print("并发查询营业部明细失败，切换到第二层数据源")
            return CapitalAnalyzer._get_sina_data()

        except Exception as e:
            print(f"分析龙虎榜游资失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '分析过程中发生错误，请稍后重试'
            }

    @staticmethod
    @retry_with_backoff(max_retries=3, backoff_factor=2)
    def _get_seat_detail_by_code(lhb_df, date=None):
        """
        使用营业部代码查询详细数据（带重试机制）
        """
        try:
            import akshare as ak

            # 从龙虎榜数据中提取营业部代码（如果有）
            # 注意：stock_lhb_detail_em 不直接返回营业部代码
            # 我们需要通过其他方式获取营业部代码

            # 方案：从新浪接口获取活跃营业部列表，然后查询详细数据
            try:
                # 检查缓存
                cache_key = f"sina_yyb_stats_{date or 'latest'}"
                cached_data = CapitalAnalyzer.cache.get(cache_key)
                if cached_data:
                    print(f"从缓存获取新浪营业部数据")
                    yyb_stats = pd.DataFrame(cached_data)
                else:
                    # 获取新浪营业部统计数据
                    yyb_stats = ak.stock_lhb_yytj_sina(symbol='5')
                    if not yyb_stats.empty:
                        # 缓存数据，TTL为1小时
                        CapitalAnalyzer.cache.set(cache_key, yyb_stats.to_dict('records'), ttl=3600)

                if yyb_stats.empty:
                    print("新浪接口返回空数据")
                    return None

                print(f"从新浪接口获取到 {len(yyb_stats)} 个营业部")

                # 筛选出在龙虎榜中的营业部
                # 通过营业部名称匹配
                matched_seats = []

                # 构建营业部名称列表（用于匹配）
                seat_names = []
                for _, row in yyb_stats.iterrows():
                    for col in yyb_stats.columns:
                        if '营业部' in col or '席位' in col:
                            seat_name = str(row.get(col, ''))
                            if seat_name and seat_name not in seat_names:
                                seat_names.append(seat_name)
                            break

                print(f"新浪接口中的营业部数量: {len(seat_names)}")
                print(f"营业部示例: {seat_names[:5]}")

                # 如果没有营业部信息，返回None
                if not seat_names:
                    return None

                # 如果获取到了营业部代码，可以尝试查询详细数据
                # 但是由于营业部代码需要从 stock_lhb_hyyyb_em 获取，而该接口数据过时
                # 所以这里我们直接使用新浪接口的统计数据

                return CapitalAnalyzer._analyze_sina_seat_data(yyb_stats, date)

            except Exception as e:
                print(f"获取营业部详细数据失败: {e}")
                import traceback
                traceback.print_exc()
                return None

        except Exception as e:
            print(f"查询营业部详细数据失败: {e}")
            raise

    @staticmethod
    @retry_with_backoff(max_retries=3, backoff_factor=2)
    def _get_seat_detail_by_stock_concurrent(lhb_df, date_str, max_workers=10):
        """
        方案1+3：按股票逐个查询营业部明细（并发优化）

        Args:
            lhb_df: 龙虎榜股票列表
            date_str: 日期字符串（格式：YYYYMMDD）
            max_workers: 最大并发线程数

        Returns:
            游资分析结果
        """
        try:
            import akshare as ak
            from concurrent.futures import ThreadPoolExecutor, as_completed

            all_seats = []
            success_count = 0
            fail_count = 0

            def fetch_seat_detail(stock_info):
                """获取单个股票的营业部明细"""
                code = stock_info['代码']
                name = stock_info['名称']

                try:
                    # 使用正确的接口：按股票代码查询营业部明细
                    seats = ak.stock_lhb_stock_detail_em(
                        symbol=code,
                        date=date_str
                    )

                    if not seats.empty:
                        # 添加股票信息
                        seats['股票代码'] = code
                        seats['股票名称'] = name
                        seats['上榜日'] = date_str
                        return seats, True
                    else:
                        return None, False
                except Exception as e:
                    print(f"  [WARN] {name}({code}) 查询失败: {e}")
                    return None, False

            # 并发查询
            print(f"[START] 开始并发查询 {len(lhb_df)} 只股票的营业部明细（线程数: {max_workers}）")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                futures = {
                    executor.submit(fetch_seat_detail, row): idx
                    for idx, row in lhb_df.iterrows()
                }

                # 收集结果
                for future in as_completed(futures):
                    result, success = future.result()
                    if success and result is not None:
                        all_seats.append(result)
                        success_count += 1
                        print(f"  [OK] 成功获取 {success_count}/{len(lhb_df)}")
                    else:
                        fail_count += 1

            print(f"[OK] 并发查询完成：成功 {success_count} 只，失败 {fail_count} 只")

            if not all_seats:
                print("[ERROR] 所有股票的营业部明细查询均失败")
                return None

            # 合并所有营业部数据
            df_all = pd.concat(all_seats, ignore_index=True)
            print(f"[OK] 总计获取 {len(df_all)} 条营业部明细数据")

            # 分析营业部数据
            return CapitalAnalyzer._analyze_seat_data_from_stock_detail(df_all)

        except Exception as e:
            print(f"[ERROR] 并发查询营业部明细失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def _analyze_seat_data_from_stock_detail(df_all, date_str=None):
        """
        分析从股票明细获取的营业部数据

        Args:
            df_all: 营业部明细数据
            date_str: 日期字符串（用于缓存）

        Returns:
            游资分析结果
        """
        try:
            capital_analysis = []
            capital_stats = {}
            matched_count = 0

            # 检查列名
            if '营业部名称' not in df_all.columns:
                # 尝试找到营业部名称列
                seat_col = None
                for col in df_all.columns:
                    if '营业' in col or '席位' in col:
                        seat_col = col
                        break

                if seat_col is None:
                    print("[ERROR] 营业部明细数据中找不到营业部名称列")
                    return None

                df_all = df_all.rename(columns={seat_col: '营业部名称'})

            print(f"[OK] 营业部明细列名: {df_all.columns.tolist()}")

            # 分析每条营业部记录
            for _, row in df_all.iterrows():
                seat_name = str(row.get('营业部名称', ''))

                if not seat_name:
                    continue

                # 使用智能匹配算法
                capital_name, match_score = CapitalAnalyzer._match_capital_seat(seat_name)

                # 只保留匹配度较高的结果（> 0.3）
                if capital_name and match_score > 0.3:
                    matched_count += 1

                    # 统计游资操作
                    if capital_name not in capital_stats:
                        capital_stats[capital_name] = {
                            '买入次数': 0,
                            '卖出次数': 0,
                            '买入金额': 0,
                            '卖出金额': 0,
                            '操作股票': []
                        }

                    # 获取买入和卖出金额
                    buy_amount = row.get('买入额', 0) or row.get('买入', 0) or 0
                    sell_amount = row.get('卖出额', 0) or row.get('卖出', 0) or 0

                    # 获取买入和卖出次数
                    buy_count = 1 if buy_amount > 0 else 0
                    sell_count = 1 if sell_amount > 0 else 0

                    if buy_amount > 0:
                        capital_stats[capital_name]['买入次数'] += buy_count
                        capital_stats[capital_name]['买入金额'] += buy_amount
                    if sell_amount > 0:
                        capital_stats[capital_name]['卖出次数'] += sell_count
                        capital_stats[capital_name]['卖出金额'] += sell_amount

                    # 记录操作股票
                    stock_info = {
                        '代码': row.get('股票代码', ''),
                        '名称': row.get('股票名称', ''),
                        '日期': row.get('上榜日', ''),
                        '买入金额': buy_amount,
                        '卖出金额': sell_amount,
                        '净买入': buy_amount - sell_amount
                    }
                    capital_stats[capital_name]['操作股票'].append(stock_info)

                    capital_analysis.append({
                        '游资名称': capital_name,
                        '营业部名称': seat_name,
                        '股票代码': row.get('股票代码', ''),
                        '股票名称': row.get('股票名称', ''),
                        '上榜日': row.get('上榜日', ''),
                        '买入金额': buy_amount,
                        '卖出金额': sell_amount,
                        '净买入': buy_amount - sell_amount
                    })

            # 计算游资统计
            capital_summary = []
            for capital_name, stats in capital_stats.items():
                net_flow = stats['买入金额'] - stats['卖出金额']
                total_trades = stats['买入次数'] + stats['卖出次数']

                # 判断操作风格
                if stats['买入金额'] > stats['卖出金额'] * 2:
                    style = "激进买入"
                elif stats['卖出金额'] > stats['买入金额'] * 2:
                    style = "激进卖出"
                elif net_flow > 0:
                    style = "偏多"
                else:
                    style = "偏空"

                capital_summary.append({
                    '游资名称': capital_name,
                    '买入次数': stats['买入次数'],
                    '卖出次数': stats['卖出次数'],
                    '总操作次数': total_trades,
                    '买入金额': stats['买入金额'],
                    '卖出金额': stats['卖出金额'],
                    '净流入': net_flow,
                    '操作风格': style,
                    '操作股票数': len(stats['操作股票'])
                })

            # 按净流入排序
            capital_summary.sort(key=lambda x: x['净流入'], reverse=True)

            print(f"[OK] 分析完成：匹配到 {matched_count} 条游资操作记录，涉及 {len(capital_stats)} 个游资")

            result = {
                '数据状态': '正常',
                '游资统计': capital_summary,
                '游资操作记录': capital_analysis,
                '匹配记录数': matched_count,
                '游资数量': len(capital_stats),
                '龙虎榜总记录数': len(df_all),
                '说明': f'通过并发查询获取营业部明细，在 {len(df_all)} 条记录中找到 {matched_count} 条游资操作记录'
            }

            # 保存到缓存
            cache_key = f"lhb_capital_concurrent_{date_str}"
            CapitalAnalyzer.cache.set(cache_key, result, ttl=3600)  # 缓存1小时

            return result

        except Exception as e:
            print(f"[ERROR] 分析营业部明细数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    @retry_with_backoff(max_retries=3, backoff_factor=2)
    def _get_sina_data():
        """
        第二层数据源：新浪接口（带重试机制）
        获取营业部统计数据
        """
        try:
            import akshare as ak

            print("=" * 60)
            print("第二层数据源：新浪接口")
            print("=" * 60)

            # 检查缓存
            cache_key = "sina_yyb_stats_latest"
            cached_data = CapitalAnalyzer.cache.get(cache_key)
            if cached_data:
                print(f"从缓存获取新浪营业部数据")
                yyb_stats = pd.DataFrame(cached_data)
            else:
                # 使用新浪接口获取营业部统计数据
                yyb_stats = ak.stock_lhb_yytj_sina(symbol='5')  # 获取最近5天的数据
                if not yyb_stats.empty:
                    # 缓存数据，TTL为1小时
                    CapitalAnalyzer.cache.set(cache_key, yyb_stats.to_dict('records'), ttl=3600)

            if yyb_stats.empty:
                print("新浪接口返回空数据，切换到第三层数据源")
                return CapitalAnalyzer._get_historical_data()

            print(f"获取到 {len(yyb_stats)} 条营业部统计数据")
            print(f"新浪数据列名: {yyb_stats.columns.tolist()}")

            return CapitalAnalyzer._analyze_sina_seat_data(yyb_stats)

        except Exception as e:
            print(f"获取新浪营业部数据失败: {e}")
            import traceback
            traceback.print_exc()
            return CapitalAnalyzer._get_historical_data()

    @staticmethod
    def _analyze_sina_seat_data(yyb_stats, date=None):
        """
        分析新浪接口的营业部数据
        """
        try:
            # 构建席位数据
            all_seat_data = []
            for _, row in yyb_stats.head(50).iterrows():  # 取前50条
                # 找到营业部名称列
                seat_name = ''
                for col in yyb_stats.columns:
                    if '营业部' in col or '席位' in col:
                        seat_name = str(row.get(col, ''))
                        break

                if not seat_name:
                    continue

                # 处理金额数据（累积购买额和累积卖出额）
                buy_amount = row.get('累积购买额', 0)
                sell_amount = row.get('累积卖出额', 0)

                # 确保金额是数值类型
                if pd.notna(buy_amount):
                    try:
                        buy_amount = float(buy_amount)
                    except:
                        buy_amount = 0
                else:
                    buy_amount = 0

                if pd.notna(sell_amount):
                    try:
                        sell_amount = float(sell_amount)
                    except:
                        sell_amount = 0
                else:
                    sell_amount = 0

                # 获取买入和卖出次数
                buy_count = row.get('买入席位数', 0)
                sell_count = row.get('卖出席位数', 0)

                if pd.notna(buy_count):
                    try:
                        buy_count = int(buy_count)
                    except:
                        buy_count = 0
                else:
                    buy_count = 0

                if pd.notna(sell_count):
                    try:
                        sell_count = int(sell_count)
                    except:
                        sell_count = 0
                else:
                    sell_count = 0

                all_seat_data.append({
                    '代码': '',
                    '名称': str(row.get('买入前三股票', '')),
                    '上榜日': date if date else '2026-01-06',
                    '收盘价': 0,
                    '涨跌幅': 0,
                    '营业部名称': seat_name,
                    '买入额': buy_amount,
                    '卖出额': sell_amount,
                    '净买入': buy_amount - sell_amount,
                    '买入次数': buy_count,
                    '卖出次数': sell_count
                })

            if all_seat_data:
                seat_df = pd.DataFrame(all_seat_data)
                print(f"成功构建席位数据，共 {len(seat_df)} 条记录")
                print(f"样本数据:\n{seat_df.head(3).to_string()}")
                return CapitalAnalyzer._analyze_seat_data(seat_df, '营业部名称', is_sina=True)
            else:
                print("新浪数据中没有有效的席位信息")
                return CapitalAnalyzer._get_historical_data()

        except Exception as e:
            print(f"分析新浪营业部数据失败: {e}")
            import traceback
            traceback.print_exc()
            return CapitalAnalyzer._get_historical_data()

    @staticmethod
    def _get_historical_data():
        """
        第三层数据源：本地缓存/历史数据
        """
        try:
            import akshare as ak

            print("=" * 60)
            print("第三层数据源：历史营业部数据")
            print("=" * 60)

            # 尝试获取历史营业部数据
            active_yyb = ak.stock_lhb_hyyyb_em()
            if not active_yyb.empty:
                print(f"获取到 {len(active_yyb)} 条历史营业部数据")
                # 返回历史营业部数据
                return {
                    '数据状态': '正常',
                    '说明': '当前数据源不提供当日营业部明细，显示历史活跃营业部数据（数据可能过时）',
                    '活跃营业部': active_yyb,
                    '营业部数量': len(active_yyb)
                }
            else:
                print("历史营业部数据为空")
                return {
                    '数据状态': '无数据',
                    '说明': '所有数据源均无法获取到有效数据，请稍后重试'
                }

        except Exception as e:
            print(f"获取历史营业部数据失败: {e}")
            return {
                '数据状态': '获取数据失败',
                '错误信息': str(e),
                '说明': '所有数据源均无法获取到有效数据，请稍后重试'
            }

    @staticmethod
    def _match_capital_seat(seat_name):
        """
        智能匹配游资席位

        使用多级匹配策略：
        1. 精确匹配：完全匹配
        2. 关键词匹配：包含关键词
        3. 模糊匹配：去除空格和特殊字符后匹配

        Returns:
            tuple: (capital_name, match_score) 或 (None, 0)
        """
        # 标准化营业部名称：去除空格和特殊字符
        normalized_name = seat_name.replace(' ', '').replace('　', '').replace('（', '(').replace('）', ')')

        for capital_name, seats in CapitalAnalyzer.FAMOUS_CAPITALISTS.items():
            # 1. 精确匹配
            if seat_name in seats or normalized_name in seats:
                return capital_name, 1.0

            # 2. 关键词匹配
            for seat_pattern in seats:
                if seat_pattern in seat_name or seat_pattern in normalized_name:
                    # 计算匹配度：关键词长度 / 总长度
                    match_score = len(seat_pattern) / len(seat_name)
                    return capital_name, match_score

            # 3. 模糊匹配：去除"证券营业部"、"股份有限公司"等后缀
            simplified_name = normalized_name.replace('证券营业部', '').replace('股份有限公司', '').replace('证券', '')
            simplified_pattern = [s.replace('证券营业部', '').replace('股份有限公司', '').replace('证券', '') for s in seats]

            for i, pattern in enumerate(simplified_pattern):
                if pattern in simplified_name:
                    match_score = len(pattern) / len(simplified_name)
                    return capital_name, match_score * 0.9  # 降低匹配度

        return None, 0.0

    @staticmethod
    def _analyze_seat_data(lhb_df, seat_col, is_sina=False):
        """
        分析营业部数据（优化游资识别精度）
        """
        try:
            # 分析游资席位
            capital_analysis = []
            capital_stats = {}
            matched_count = 0

            unique_seats = lhb_df[seat_col].unique()
            print(f"共找到 {len(unique_seats)} 个不同的营业部")
            print(f"营业部列表: {unique_seats[:10]}...")  # 只打印前10个

            for _, row in lhb_df.iterrows():
                seat_name = str(row[seat_col])

                # 使用智能匹配算法
                capital_name, match_score = CapitalAnalyzer._match_capital_seat(seat_name)

                # 只保留匹配度较高的结果（> 0.3）
                if capital_name and match_score > 0.3:
                        matched_count += 1
                        # 统计游资操作
                        if capital_name not in capital_stats:
                            capital_stats[capital_name] = {
                                '买入次数': 0,
                                '卖出次数': 0,
                                '买入金额': 0,
                                '卖出金额': 0,
                                '操作股票': []
                            }

                        # 判断买卖方向
                        # 新浪数据使用累积购买额和累积卖出额
                        buy_amount = row.get('买入额', 0)
                        sell_amount = row.get('卖出额', 0)

                        # 获取买入和卖出次数
                        buy_count = row.get('买入次数', 0)
                        sell_count = row.get('卖出次数', 0)

                        if buy_amount > 0 or buy_count > 0:
                            capital_stats[capital_name]['买入次数'] += buy_count if buy_count > 0 else 1
                            capital_stats[capital_name]['买入金额'] += buy_amount
                        if sell_amount > 0 or sell_count > 0:
                            capital_stats[capital_name]['卖出次数'] += sell_count if sell_count > 0 else 1
                            capital_stats[capital_name]['卖出金额'] += sell_amount

                        # 记录操作股票
                        stock_info = {
                            '代码': row['代码'],
                            '名称': row['名称'],
                            '日期': row['上榜日'],
                            '买入金额': buy_amount,
                            '卖出金额': sell_amount,
                            '净买入': buy_amount - sell_amount
                        }
                        capital_stats[capital_name]['操作股票'].append(stock_info)

                        capital_analysis.append({
                            '游资名称': capital_name,
                            '营业部名称': row[seat_col],
                            '股票代码': row['代码'],
                            '股票名称': row['名称'],
                            '上榜日': row['上榜日'],
                            '买入金额': buy_amount,
                            '卖出金额': sell_amount,
                            '净买入': buy_amount - sell_amount
                        })

            # 计算游资统计
            capital_summary = []
            for capital_name, stats in capital_stats.items():
                net_flow = stats['买入金额'] - stats['卖出金额']
                total_trades = stats['买入次数'] + stats['卖出次数']

                # 判断操作风格
                if stats['买入金额'] > stats['卖出金额'] * 2:
                    style = "激进买入"
                elif stats['卖出金额'] > stats['买入金额'] * 2:
                    style = "激进卖出"
                elif net_flow > 0:
                    style = "偏多"
                else:
                    style = "偏空"

                capital_summary.append({
                    '游资名称': capital_name,
                    '买入次数': stats['买入次数'],
                    '卖出次数': stats['卖出次数'],
                    '总操作次数': total_trades,
                    '买入金额': stats['买入金额'],
                    '卖出金额': stats['卖出金额'],
                    '净流入': net_flow,
                    '操作风格': style,
                    '操作股票数': len(stats['操作股票'])
                })

            # 按净流入排序
            capital_summary.sort(key=lambda x: x['净流入'], reverse=True)

            print(f"分析完成：匹配到 {matched_count} 条游资操作记录，涉及 {len(capital_stats)} 个游资")

            result = {
                '数据状态': '正常',
                '游资统计': capital_summary,
                '游资操作记录': capital_analysis,
                '匹配记录数': matched_count,
                '游资数量': len(capital_stats),
                '龙虎榜总记录数': len(lhb_df),
                '说明': f'在 {len(lhb_df)} 条龙虎榜记录中，找到 {matched_count} 条游资操作记录'
            }

            # 保存到缓存
            cache_key = f"lhb_capital_{is_sina and 'sina' or 'latest'}"
            CapitalAnalyzer.cache.set(cache_key, result, ttl=3600)  # 缓存1小时

            return result

        except Exception as e:
            return {
                '数据状态': '获取失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def track_capital_pattern(capital_name, days=30):
        """
        追踪游资操作模式
        分析特定游资在指定时间内的操作规律
        """
        try:
            import akshare as ak

            if capital_name not in CapitalAnalyzer.FAMOUS_CAPITALISTS:
                return {
                    '数据状态': '未知游资',
                    '说明': f'未找到游资: {capital_name}'
                }

            # 获取该游资的席位列表
            seats = CapitalAnalyzer.FAMOUS_CAPITALISTS[capital_name]
            print(f"游资 {capital_name} 的席位列表: {seats}")

            # 获取历史龙虎榜数据
            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=days)

            all_operations = []
            checked_dates = 0
            matched_dates = 0

            # 获取每日龙虎榜数据
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y%m%d")
                checked_dates += 1

                try:
                    lhb_df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)

                    if not lhb_df.empty:
                        print(f"{date_str}: 获取 {len(lhb_df)} 条龙虎榜记录")

                        # 筛选该游资的操作（使用模糊匹配）
                        # 检查列名是否存在
                        if '营业部名称' in lhb_df.columns:
                            seat_col = '营业部名称'
                        elif '营业部' in lhb_df.columns:
                            seat_col = '营业部'
                        elif '营业部' in str(lhb_df.columns):
                            seat_col = '营业部名称'
                        else:
                            # 尝试找到包含"营业部"的列
                            seat_col = None
                            for col in lhb_df.columns:
                                if '营业' in col:
                                    seat_col = col
                                    break

                        if seat_col is None:
                            print(f"  未找到营业部列，可用列: {lhb_df.columns.tolist()}")
                            current_date += pd.Timedelta(days=1)
                            continue

                        for _, row in lhb_df.iterrows():
                            seat_name = str(row[seat_col])

                            # 精确匹配或模糊匹配
                            if seat_name in seats or any(keyword in seat_name for keyword in seats):
                                matched_dates += 1
                                all_operations.append({
                                    '日期': row.get('交易日期', row.get('上榜日', date_str)),
                                    '股票代码': row['代码'],
                                    '股票名称': row['名称'],
                                    '买入金额': row.get('买入额', row.get('买入金额', 0)),
                                    '卖出金额': row.get('卖出额', row.get('卖出金额', 0)),
                                    '净买入': row.get('买入额', row.get('买入金额', 0)) - row.get('卖出额', row.get('卖出金额', 0)),
                                    '营业部名称': seat_name
                                })
                                print(f"  匹配: {seat_name} - {row['名称']}({row['代码']})")
                except Exception as e:
                    print(f"{date_str}: 获取数据失败 - {e}")
                    pass

                current_date += pd.Timedelta(days=1)

            print(f"检查了 {checked_dates} 天，{matched_dates} 天找到操作记录，共 {len(all_operations)} 条操作")

            # 如果没有操作记录，尝试使用新浪接口获取营业部数据
            if not all_operations:
                print("龙虎榜数据中无营业部信息，尝试使用新浪接口获取营业部数据")

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # 获取新浪营业部统计数据
                        yyb_stats = ak.stock_lhb_yytj_sina(symbol='30')  # 获取最近30天的数据

                        if not yyb_stats.empty:
                            print(f"获取到 {len(yyb_stats)} 条营业部统计数据")

                            # 筛选该游资的营业部
                            matched_yyb = []
                            for _, row in yyb_stats.iterrows():
                                seat_name = str(row['营业部名称'])

                                # 精确匹配或模糊匹配
                                if seat_name in seats or any(keyword in seat_name for keyword in seats):
                                    # 处理金额数据
                                    buy_amount = row.get('买入总额', 0)
                                    sell_amount = row.get('卖出总额', 0)

                                    # 确保金额是数值类型
                                    if pd.notna(buy_amount):
                                        try:
                                            buy_amount = float(buy_amount)
                                        except:
                                            buy_amount = 0
                                    else:
                                        buy_amount = 0

                                    if pd.notna(sell_amount):
                                        try:
                                            sell_amount = float(sell_amount)
                                        except:
                                            sell_amount = 0
                                    else:
                                        sell_amount = 0

                                    matched_yyb.append({
                                        '日期': row['上榜日期'],
                                        '股票代码': '',  # 新浪数据中没有股票代码
                                        '股票名称': str(row.get('操作前股票', '')),
                                        '买入金额': buy_amount,
                                        '卖出金额': sell_amount,
                                        '净买入': buy_amount - sell_amount,
                                        '营业部名称': seat_name
                                    })

                            if matched_yyb:
                                print(f"从新浪数据中找到 {len(matched_yyb)} 条操作记录")

                                # 分析操作模式
                                df_ops = pd.DataFrame(matched_yyb)

                                # 1. 操作频率
                                operation_frequency = len(matched_yyb) / days if days > 0 else 0

                                # 2. 买入比例
                                buy_count = len(df_ops[df_ops['净买入'] > 0])
                                sell_count = len(df_ops[df_ops['净买入'] < 0])
                                buy_ratio = round(buy_count / len(df_ops) * 100, 2) if len(df_ops) > 0 else 0

                                # 3. 总金额
                                total_buy = df_ops['买入金额'].sum()
                                total_sell = df_ops['卖出金额'].sum()

                                # 4. 操作风格
                                net_flow = total_buy - total_sell
                                if total_buy > total_sell * 2:
                                    style = "激进买入"
                                elif total_sell > total_buy * 2:
                                    style = "激进卖出"
                                elif net_flow > 0:
                                    style = "偏多"
                                else:
                                    style = "偏空"

                                # 5. 操作成功率（简化版）
                                success_rate = 50.0  # 新浪数据无法计算准确的成功率

                                return {
                                    '数据状态': '正常',
                                    '数据来源': '新浪数据',
                                    '操作次数': len(matched_yyb),
                                    '操作频率': operation_frequency,
                                    '买入比例': buy_ratio,
                                    '操作成功率': success_rate,
                                    '操作风格': style,
                                    '总买入金额': total_buy,
                                    '总卖出金额': total_sell,
                                    '操作记录': matched_yyb,
                                    '说明': f'基于新浪数据分析，{capital_name} 共有 {len(matched_yyb)} 次操作记录'
                                }
                            else:
                                print(f"新浪数据中未找到 {capital_name} 的操作记录")
                        else:
                            print("新浪数据为空")
                    except Exception as e:
                        print(f"获取新浪营业部数据失败（尝试 {attempt + 1}/{max_retries}）: {e}")
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(2)  # 等待2秒后重试
                        else:
                            print(f"所有重试均失败")

                # 如果历史数据也没有，返回提示信息
                return {
                    '数据状态': '无操作记录',
                    '说明': f'{capital_name} 在最近 {days} 天内无操作记录。可能原因：1) 该游资近期未上榜 2) 席位名称不匹配 3) 数据源限制。当前数据源不提供营业部明细，无法追踪游资操作。',
                    '检查天数': checked_dates,
                    '匹配天数': matched_dates,
                    '游资席位': seats
                }

            # 分析操作模式
            df_ops = pd.DataFrame(all_operations)

            # 1. 操作频率
            operation_frequency = len(all_operations) / days

            # 2. 买卖偏好
            total_buy = df_ops['买入金额'].sum()
            total_sell = df_ops['卖出金额'].sum()
            buy_ratio = total_buy / (total_buy + total_sell) if (total_buy + total_sell) > 0 else 0

            # 3. 单次操作金额
            avg_operation_amount = df_ops['净买入'].abs().mean()

            # 4. 操作成功率（后续3天涨幅）
            success_count = 0
            total_count = 0

            db = DataManager()
            for op in all_operations:
                try:
                    symbol = op['股票代码']
                    op_date = op['日期']

                    # 获取历史数据
                    start_date_str = op_date
                    end_date_str = (pd.Timestamp(op_date) + pd.Timedelta(days=5)).strftime("%Y-%m-%d")

                    df = db.get_history_data(symbol, start_date=start_date_str, end_date=end_date_str)

                    if not df.empty and len(df) > 3:
                        # 计算操作后3天的涨幅
                        op_price = df.iloc[0]['close']
                        future_price = df.iloc[3]['close']
                        future_return = (future_price - op_price) / op_price * 100

                        if future_return > 0:
                            success_count += 1
                        total_count += 1
                except:
                    pass

            db.close()

            success_rate = (success_count / total_count * 100) if total_count > 0 else 0

            # 5. 判断操作风格
            if buy_ratio > 0.7:
                style = "激进买入型"
            elif buy_ratio < 0.3:
                style = "激进卖出型"
            elif avg_operation_amount > 50000000:
                style = "大资金操作型"
            else:
                style = "平均操作"

            return {
                '数据状态': '正常',
                '游资名称': capital_name,
                '分析天数': days,
                '操作次数': len(all_operations),
                '操作频率': round(operation_frequency, 2),
                '总买入金额': total_buy,
                '总卖出金额': total_sell,
                '买入比例': round(buy_ratio * 100, 1),
                '平均操作金额': round(avg_operation_amount, 0),
                '操作成功率': round(success_rate, 1),
                '操作风格': style,
                '操作记录': all_operations
            }

        except Exception as e:
            return {
                '数据状态': '分析失败',
                '错误信息': str(e),
                '说明': '可能是网络问题或数据源限制'
            }

    @staticmethod
    def predict_capital_next_move(capital_name):
        """
        预测游资下一步操作
        基于历史操作模式预测
        """
        try:
            # 获取游资操作模式
            pattern_result = CapitalAnalyzer.track_capital_pattern(capital_name, days=30)

            if pattern_result['数据状态'] != '正常':
                return pattern_result

            # 获取最近操作
            recent_operations = pattern_result['操作记录'][-5:]  # 最近5次操作

            # 分析最近操作方向
            recent_buy = sum(op['买入金额'] for op in recent_operations)
            recent_sell = sum(op['卖出金额'] for op in recent_operations)

            # 预测
            predictions = []

            if recent_buy > recent_sell * 2:
                predictions.append({
                    '预测类型': '继续买入',
                    '概率': '高',
                    '说明': f'{capital_name} 最近大举买入，可能继续加仓'
                })
            elif recent_sell > recent_buy * 2:
                predictions.append({
                    '预测类型': '继续卖出',
                    '概率': '高',
                    '说明': f'{capital_name} 最近大举卖出，可能继续减仓'
                })
            else:
                predictions.append({
                    '预测类型': '观望或小量操作',
                    '概率': '中',
                    '说明': f'{capital_name} 最近操作均衡，可能观望'
                })

            # 根据成功率预测
            if pattern_result['操作成功率'] > 60:
                predictions.append({
                    '预测类型': '关注其操作',
                    '概率': '中',
                    '说明': f'{capital_name} 历史成功率高，建议关注其操作'
                })

            return {
                '数据状态': '正常',
                '游资名称': capital_name,
                '预测列表': predictions
            }

        except Exception as e:
            return {
                '数据状态': '预测失败',
                '错误信息': str(e),
                '说明': '可能是数据问题'
            }