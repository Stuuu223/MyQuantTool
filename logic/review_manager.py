#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V11 核心组件：复盘管理器 (Review Manager)
负责管理'隔日记忆'，计算连板高度和昨日溢价
V18.7: 新增高价值案例自动捕获机制
"""

import pandas as pd
import json
import os
from datetime import datetime
from logic.database_manager import get_db_manager
from logic.logger import get_logger
import akshare as ak

logger = get_logger(__name__)


class ReviewManager:
    """
    V11 核心组件：复盘管理器
    负责管理'隔日记忆'，计算连板高度和昨日溢价
    V18.7: 新增高价值案例自动捕获机制
    """
    
    def __init__(self):
        self.db = get_db_manager()
        self._init_tables()
    
    def _init_tables(self):
        """初始化复盘数据表 (SQLite)"""
        # 创建每日市场概况表 (Metadata)
        sql_summary = """
        CREATE TABLE IF NOT EXISTS market_summary (
            date TEXT PRIMARY KEY,
            highest_board INTEGER,      -- 最高连板数
            limit_up_count INTEGER,     -- 涨停家数
            limit_down_count INTEGER,   -- 跌停家数
            limit_up_list TEXT,         -- 涨停股名单 (JSON)
            top_sectors TEXT,           -- [V13 新增] 存储当日领涨板块 (JSON 列表)
            created_at TEXT
        )
        """
        self.db.sqlite_execute(sql_summary)
        
        # [V13 新增] 数据库迁移：添加 top_sectors 字段（如果不存在）
        try:
            # 检查字段是否存在
            check_sql = "PRAGMA table_info(market_summary)"
            columns = self.db.sqlite_query(check_sql)
            column_names = [col[1] for col in columns]
            
            if 'top_sectors' not in column_names:
                # 添加新字段
                alter_sql = "ALTER TABLE market_summary ADD COLUMN top_sectors TEXT"
                self.db.sqlite_execute(alter_sql)
                logger.info("✅ V13 数据库迁移完成：已添加 top_sectors 字段")
            else:
                logger.info("✅ V13 复盘数据库表结构已就绪 (含板块记忆字段 top_sectors)")
        except Exception as e:
            logger.warning(f"⚠️ 数据库迁移失败: {e}")
    
    def run_daily_review(self, date=None):
        """
        执行每日复盘 (建议每日 15:30 运行)
        获取当日涨停数据并存入 DB
        [V13 新增] 自动抓取当日表现最强的行业板块
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        
        logger.info(f"🔄 开始执行 {date} 每日复盘归档...")
        
        try:
            # 1. 获取当日涨停池 (来自 AkShare)
            df = ak.stock_zt_pool_em(date=date)
            
            if df is None or df.empty:
                logger.warning(f"⚠️ {date} 没有获取到涨停数据 (可能是休市或数据未更新)")
                return False
            
            # 2. 提取核心数据
            # 连板高度 (连板数那一列的最大值)
            highest_board = int(df['连板数'].max()) if '连板数' in df.columns else 1
            limit_up_count = len(df)
            
            # 提取涨停名单 (只存代码，节省空间)
            # 格式: ["000001", "600519", ...]
            limit_up_list = df['代码'].tolist()
            
            # [V13 新增] 获取今日领涨板块
            top_sectors = []
            try:
                # 获取行业板块行情
                sector_df = ak.stock_board_industry_name_em()
                # 取涨幅前 3 的板块名称
                if not sector_df.empty and '涨跌幅' in sector_df.columns:
                    top_3_sectors = sector_df.nlargest(3, '涨跌幅')['板块名称'].tolist()
                    top_sectors = top_3_sectors
                    logger.info(f"🏆 今日核心主线预选: {top_sectors}")
                else:
                    logger.warning("⚠️ 板块数据格式异常，无法提取领涨板块")
            except Exception as e:
                logger.error(f"获取领涨板块失败: {e}")
                top_sectors = []
            
            # 3. 存入数据库
            sql = """
            INSERT OR REPLACE INTO market_summary 
            (date, highest_board, limit_up_count, limit_down_count, limit_up_list, top_sectors, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            self.db.sqlite_execute(sql, (
                date, 
                highest_board, 
                limit_up_count, 
                0,  # 跌停数暂时填0，后续可扩充
                json.dumps(limit_up_list), 
                json.dumps(top_sectors),  # ✅ 存入 JSON 化的板块列表
                datetime.now().isoformat()
            ))
            
            logger.info(f"✅ 复盘归档完成! 日期: {date}, 最高板: {highest_board}, 涨停: {limit_up_count}家, 领涨板块: {top_sectors}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 复盘归档失败: {e}")
            return False
    
    def get_yesterday_stats(self):
        """
        获取昨日市场状态 (供今日实盘使用)
        [V13 新增] 返回领涨板块数据
        """
        # 获取最近的一个交易日记录
        sql = "SELECT * FROM market_summary ORDER BY date DESC LIMIT 1"
        results = self.db.sqlite_query(sql)
        
        if not results:
            return None
        
        row = results[0]
        # 解析数据
        stats = {
            'date': row[0],
            'highest_board': row[1],
            'limit_up_count': row[2],
            'limit_up_list': json.loads(row[4]) if row[4] else []  # 这是一个代码列表
        }
        
        # [V13 新增] 解析领涨板块
        if len(row) > 5 and row[5]:
            try:
                stats['top_sectors'] = json.loads(row[5])
            except:
                stats['top_sectors'] = []
        else:
            stats['top_sectors'] = []
        
        return stats
    
    def capture_golden_cases(self, date_str=None):
        """
        🚀 [V18.7 新增] 高价值案例自动捕获机制
        自动筛选：标准真龙、惨案大坑、弱转强
        
        Args:
            date_str: 日期字符串，格式 YYYYMMDD，默认为今天
        
        Returns:
            dict: 高价值案例数据，包含：
                - date: 日期
                - dragons: 标准真龙列表
                - traps: 惨案大坑列表
                - reversals: 弱转强/反核列表
                - market_score: 市场情绪评分 (0-100)
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")
        
        logger.info(f"🦁 正在捕获 {date_str} 的高价值复盘案例...")
        
        cases = {
            "date": date_str,
            "dragons": [],      # 标准答案
            "traps": [],        # 避坑指南
            "reversals": [],    # 弱转强/反核
            "market_score": 0   # 市场情绪评分
        }
        
        try:
            # 1. 获取当日涨停池 (真龙源头)
            df_zt = ak.stock_zt_pool_em(date=date_str)
            if df_zt is not None and not df_zt.empty:
                # 筛选规则：连板高度最高 Or 封板资金最大
                # 按连板数降序，封板资金降序
                df_zt['封板资金'] = df_zt['封板资金'].astype(float)
                top_dragons = df_zt.sort_values(by=['连板数', '封板资金'], ascending=[False, False]).head(3)
                
                for _, row in top_dragons.iterrows():
                    cases['dragons'].append({
                        "code": row['代码'],
                        "name": row['名称'],
                        "reason": f"🔥 市场最高标: {row['连板数']}连板, 封单{int(row['封板资金']/10000)}万",
                        "type": "SPACE_DRAGON", # 空间龙
                        "limit_board": int(row['连板数']),
                        "seal_amount": float(row['封板资金'])
                    })
                
                # 计算市场情绪评分 (0-100)
                cases['market_score'] = int(len(df_zt) / 50 * 100)
            else:
                # 如果没有涨停数据，市场情绪评分设为 20
                cases['market_score'] = 20
            
            # 2. 获取当日跌幅榜 (大坑源头) - 使用超时处理
            # 注意：akshare 获取实时行情按跌幅排序
            try:
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("获取跌幅榜超时")
                
                # 设置 30 秒超时
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(30)
                
                df_market = ak.stock_zh_a_spot_em()
                
                # 取消超时
                signal.alarm(0)
                
                # 筛选跌幅前3且成交额不为0的
                df_drop = df_market[df_market['成交额'] > 0].sort_values(by='涨跌幅').head(3)
                
                for _, row in df_drop.iterrows():
                    # 过滤掉 ST 和退市股 (如果不玩垃圾股的话)
                    if 'ST' not in row['名称'] and '退' not in row['名称']:
                        cases['traps'].append({
                            "code": row['代码'],
                            "name": row['名称'],
                            "reason": f"💀 核按钮惨案: 跌幅 {row['涨跌幅']}%, 成交{int(row['成交额']/10000)}万",
                            "type": "FATAL_TRAP",
                            "change_pct": float(row['涨跌幅']),
                            "amount": float(row['成交额'])
                        })
            except (TimeoutError, Exception) as e:
                logger.warning(f"⚠️ 获取跌幅榜失败或超时: {e}")
            
            # 3. (可选) 识别当日"炸板大面" (曾经涨停，收盘大跌)
            try:
                df_zha = ak.stock_zt_pool_zbgc_em(date=date_str) # 炸板股池
                if df_zha is not None and not df_zha.empty:
                    worst_zha = df_zha.sort_values(by='涨跌幅').head(1) # 炸得最惨的
                    for _, row in worst_zha.iterrows():
                        cases['traps'].append({
                            "code": row['代码'],
                            "name": row['名称'],
                            "reason": f"🩸 炸板大面: 涨停被砸至 {row['涨跌幅']}%, 也就是所谓的'天地板'风险",
                            "type": "FAILED_DRAGON",
                            "change_pct": float(row['涨跌幅'])
                        })
            except Exception as e:
                logger.warning(f"⚠️ 获取炸板股失败: {e}")
            
            # 4. 保存案例集
            save_dir = "data/review_cases/golden_cases"
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            file_path = f"{save_dir}/cases_{date_str}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cases, f, ensure_ascii=False, indent=4)
            
            logger.info(f"✅ 高价值案例已归档: {file_path}")
            logger.info(f"   - 真龙: {len(cases['dragons'])} 只")
            logger.info(f"   - 大坑: {len(cases['traps'])} 只")
            logger.info(f"   - 炸板: {len([t for t in cases['traps'] if t['type'] == 'FAILED_DRAGON'])} 只")
            logger.info(f"   - 市场情绪评分: {cases['market_score']}")
            
            return cases
        
        except Exception as e:
            logger.error(f"❌ 案例捕获失败: {e}")
            import traceback
            traceback.print_exc()
            return None


# 单例测试
if __name__ == "__main__":
    rm = ReviewManager()
    # 尝试跑一下最近一个交易日的数据 (注意：如果是周末可能取不到今天的，akshare通常延迟)
    # 我们可以尝试取上周五的数据测试
    rm.run_daily_review(date='20260116')
    
    # 读取测试
    stats = rm.get_yesterday_stats()
    print("读取到的昨日状态:", stats)
    
    # 测试高价值案例捕获
    print("\n" + "="*60)
    print("测试高价值案例捕获")
    print("="*60)
    golden_cases = rm.capture_golden_cases(date='20260116')
    if golden_cases:
        print(f"✅ 捕获成功!")
        print(f"   - 日期: {golden_cases['date']}")
        print(f"   - 真龙: {len(golden_cases['dragons'])} 只")
        print(f"   - 大坑: {len(golden_cases['traps'])} 只")
        print(f"   - 炸板: {len([t for t in golden_cases['traps'] if t['type'] == 'FAILED_DRAGON'])} 只")
    else:
        print("❌ 捕获失败")