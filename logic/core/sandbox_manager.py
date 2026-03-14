#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
沙盒档案库管理器 - CTO V169 规范化输出架构
================================================================

【Boss指令】
"先把日志、运行文件创建好归类好，方便以后研究、翻查、搜寻，再说连续回测"

【架构设计】
每次运行（无论单日还是多日连续）都在 data/backtest_out/ 下创建独立沙盒：

data/backtest_out/
└── run_20260314_153022/              # 以运行启动时间戳命名（防覆盖）
    ├── config_snapshot.json          # 本次回测使用的参数（防作弊）
    ├── daily_ledgers/                # 每分钟的Top10 CSV
    │   ├── top10_ledger_20260309.csv
    │   └── top10_ledger_20260310.csv
    ├── battle_reports/               # 每日战报档案
    │   ├── report_20260309.md        # 人类可读的Markdown战报
    │   └── report_20260309.json      # 结构化数据（含案发现场快照）
    └── equity_curve.csv              # 跨日连续的资金曲线

【红线】
- 只要是运行产生的输出，必须存入沙盒
- 禁止随意在项目其他目录创建文件
- Run ID必须唯一，多次运行不能互相覆盖
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKTEST_OUT_ROOT = PROJECT_ROOT / "data" / "backtest_out"


class SandboxManager:
    """沙盒档案库管理器 - 统一管理所有运行时输出"""
    
    def __init__(self, run_id: str = None, mode: str = "backtest"):
        """
        初始化沙盒管理器
        
        Args:
            run_id: 运行批次ID，为空则自动生成（格式：run_YYYYMMDD_HHMMSS）
            mode: 运行模式（backtest/scan/live）
        """
        self.mode = mode
        
        # 生成或使用传入的Run ID
        if run_id:
            self.run_id = run_id
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.run_id = f"run_{timestamp}"
        
        # 创建沙盒根目录
        self.sandbox_root = BACKTEST_OUT_ROOT / self.run_id
        self.daily_ledgers_dir = self.sandbox_root / "daily_ledgers"
        self.battle_reports_dir = self.sandbox_root / "battle_reports"
        
        # 初始化目录结构
        self._init_directories()
        
        logger.info(f"[SandboxManager] 沙盒已创建: {self.run_id}")
        logger.info(f"  根目录: {self.sandbox_root}")
    
    def _init_directories(self):
        """初始化沙盒目录结构"""
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        self.daily_ledgers_dir.mkdir(parents=True, exist_ok=True)
        self.battle_reports_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[SandboxManager] 目录结构初始化完成")
    
    def get_run_id(self) -> str:
        """获取当前运行批次ID"""
        return self.run_id
    
    def get_sandbox_root(self) -> Path:
        """获取沙盒根目录"""
        return self.sandbox_root
    
    # ==================== 配置快照 ====================
    
    def save_config_snapshot(self, config: Dict[str, Any]) -> Path:
        """
        保存配置快照（防止篡改和争议）
        
        Args:
            config: 配置字典
            
        Returns:
            配置文件路径
        """
        config_path = self.sandbox_root / "config_snapshot.json"
        
        # 添加元数据
        config_with_meta = {
            "run_id": self.run_id,
            "mode": self.mode,
            "created_at": datetime.now().isoformat(),
            "config": config
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_with_meta, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[SandboxManager] 配置快照已保存: {config_path}")
        return config_path
    
    # ==================== 每日审计台账 ====================
    
    def get_daily_ledger_path(self, date_str: str) -> Path:
        """
        获取每日Top10审计台账CSV路径
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            
        Returns:
            CSV文件路径
        """
        return self.daily_ledgers_dir / f"top10_ledger_{date_str}.csv"
    
    def save_daily_ledger(self, date_str: str, records: List[Dict]) -> Path:
        """
        保存每日Top10审计台账
        
        Args:
            date_str: 日期字符串
            records: 记录列表
            
        Returns:
            CSV文件路径
        """
        import pandas as pd
        
        csv_path = self.get_daily_ledger_path(date_str)
        df = pd.DataFrame(records)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"[SandboxManager] 每日台账已保存: {csv_path} ({len(records)}条)")
        return csv_path
    
    # ==================== 战报档案 ====================
    
    def get_battle_report_json_path(self, date_str: str) -> Path:
        """
        获取战报JSON路径（结构化数据，含案发现场快照）
        
        Args:
            date_str: 日期字符串
            
        Returns:
            JSON文件路径
        """
        return self.battle_reports_dir / f"report_{date_str}.json"
    
    def get_battle_report_md_path(self, date_str: str) -> Path:
        """
        获取战报Markdown路径（人类可读）
        
        Args:
            date_str: 日期字符串
            
        Returns:
            MD文件路径
        """
        return self.battle_reports_dir / f"report_{date_str}.md"
    
    def save_battle_report_json(self, date_str: str, report_data: Dict[str, Any]) -> Path:
        """
        保存结构化战报JSON（含案发现场快照）
        
        Args:
            date_str: 日期字符串
            report_data: 战报数据字典
            
        Returns:
            JSON文件路径
        """
        json_path = self.get_battle_report_json_path(date_str)
        
        # 添加元数据
        report_with_meta = {
            "run_id": self.run_id,
            "date": date_str,
            "created_at": datetime.now().isoformat(),
            **report_data
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_with_meta, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[SandboxManager] 战报JSON已保存: {json_path}")
        return json_path
    
    def save_battle_report_md(self, date_str: str, markdown_content: str) -> Path:
        """
        保存人类可读的Markdown战报
        
        Args:
            date_str: 日期字符串
            markdown_content: Markdown内容
            
        Returns:
            MD文件路径
        """
        md_path = self.get_battle_report_md_path(date_str)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"[SandboxManager] 战报MD已保存: {md_path}")
        return md_path
    
    # ==================== 资金曲线 ====================
    
    def get_equity_curve_path(self) -> Path:
        """获取资金曲线CSV路径"""
        return self.sandbox_root / "equity_curve.csv"
    
    def save_equity_curve(self, daily_snapshots: List[Dict]) -> Path:
        """
        保存跨日资金曲线
        
        Args:
            daily_snapshots: 每日快照列表
            
        Returns:
            CSV文件路径
        """
        import pandas as pd
        
        csv_path = self.get_equity_curve_path()
        df = pd.DataFrame(daily_snapshots)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"[SandboxManager] 资金曲线已保存: {csv_path}")
        return csv_path
    
    # ==================== 汇总报告 ====================
    
    def print_sandbox_summary(self):
        """打印沙盒目录结构摘要"""
        print(f"\n{'='*70}")
        print(f"📁 沙盒档案库: {self.run_id}")
        print(f"{'='*70}")
        print(f"根目录: {self.sandbox_root}")
        print(f"\n目录结构:")
        
        # 配置快照
        config_path = self.sandbox_root / "config_snapshot.json"
        if config_path.exists():
            print(f"  ├── config_snapshot.json ✓")
        else:
            print(f"  ├── config_snapshot.json (待生成)")
        
        # 每日台账
        ledger_files = list(self.daily_ledgers_dir.glob("*.csv"))
        print(f"  ├── daily_ledgers/ ({len(ledger_files)}个文件)")
        for f in sorted(ledger_files)[:3]:  # 最多显示3个
            print(f"  │     └── {f.name}")
        if len(ledger_files) > 3:
            print(f"  │     └── ... 还有{len(ledger_files)-3}个文件")
        
        # 战报
        report_files = list(self.battle_reports_dir.glob("*"))
        json_count = len(list(self.battle_reports_dir.glob("*.json")))
        md_count = len(list(self.battle_reports_dir.glob("*.md")))
        print(f"  ├── battle_reports/ ({json_count}个JSON, {md_count}个MD)")
        
        # 资金曲线
        curve_path = self.get_equity_curve_path()
        if curve_path.exists():
            print(f"  └── equity_curve.csv ✓")
        else:
            print(f"  └── equity_curve.csv (待生成)")
        
        print(f"{'='*70}\n")


def create_sandbox(mode: str = "backtest", run_id: str = None) -> SandboxManager:
    """
    工厂函数：创建沙盒管理器
    
    Args:
        mode: 运行模式
        run_id: 可选的运行ID
        
    Returns:
        SandboxManager实例
    """
    return SandboxManager(run_id=run_id, mode=mode)
