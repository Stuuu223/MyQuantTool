"""
ShortTermMemoryEngine - 跨日记忆衰减引擎

战术定位:
    盘后结算记忆写入 → 次日开盘记忆读取(衰减) → TTL湮灭清理
    
核心功能:
    1. 基因写入: 涨幅>8%且换手>5%的股票,记录blood_pct作为初始当量M0
    2. 半衰期读取: 次日开盘调用,分数乘以0.5衰减
    3. TTL湮灭: ≥2个交易日未激活,物理删除记录

技术约束:
    - JSON文件持久化于 data/memory/short_term_memory.json
    - 线程安全(文件锁机制)
    - O(1)读写性能(内存缓存+延迟写入)

Author: MyQuantTool Project
Version: V1.0.0
Date: 2026-02-27
"""

import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class MemoryGene:
    """
    记忆基因结构 - 单只股票的记忆记录
    
    Attributes:
        stock_code: 股票代码
        initial_score: 初始当量M0 (blood_pct)
        current_score: 当前衰减后的当量
        create_date: 创建日期 (YYYYMMDD)
        last_active_date: 最后激活日期 (YYYYMMDD)
        half_life_count: 半衰期计数 (被读取次数)
        metadata: 额外元数据 (涨幅、换手率等)
    """
    stock_code: str
    initial_score: float
    current_score: float
    create_date: str
    last_active_date: str
    half_life_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ShortTermMemoryEngine:
    """
    短期记忆引擎 - 跨日记忆衰减管理
    
    核心设计:
        1. 内存缓存: _memory_cache 提供O(1)访问
        2. 文件锁: _file_lock 保证线程安全
        3. 延迟写入: 批量修改后统一持久化
        
    Usage:
        >>> engine = ShortTermMemoryEngine()
        >>> 
        >>> # 盘后结算 - 写入记忆
        >>> engine.write_memory("000001.SZ", gain_pct=9.5, turnover_rate=8.2, blood_pct=85.0)
        >>> 
        >>> # 次日开盘 - 读取衰减后的记忆
        >>> score = engine.read_memory("000001.SZ")  # 85.0 * 0.5 = 42.5
        >>> 
        >>> # 定期湮灭过期记忆
        >>> engine.annihilate_expired()
    """
    
    # 基因写入阈值
    GAIN_THRESHOLD = 8.0      # 涨幅阈值: >8%
    TURNOVER_THRESHOLD = 5.0  # 换手率阈值: >5%
    
    # 衰减参数
    HALF_LIFE_FACTOR = 0.5    # 半衰期衰减系数
    TTL_DAYS = 2              # TTL湮灭天数: ≥2个交易日
    
    # 交易日缓存 (简化处理,实际应从交易日历获取)
    TRADING_DAYS_CACHE: List[str] = []
    
    def __init__(self, 
                 memory_file: Optional[str] = None,
                 auto_save: bool = True,
                 auto_save_interval: int = 60):
        """
        初始化记忆引擎
        
        Args:
            memory_file: 记忆文件路径,默认 data/memory/short_term_memory.json
            auto_save: 是否启用自动保存
            auto_save_interval: 自动保存间隔(秒)
        """
        # 默认文件路径
        if memory_file is None:
            project_root = Path(__file__).parent.parent.parent
            memory_file = project_root / "data" / "memory" / "short_term_memory.json"
        
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 线程锁
        self._file_lock = threading.RLock()
        self._cache_lock = threading.RLock()
        
        # 内存缓存: {stock_code: MemoryGene}
        self._memory_cache: Dict[str, MemoryGene] = {}
        
        # 脏标记
        self._dirty = False
        self._last_save_time = time.time()
        self._auto_save = auto_save
        self._auto_save_interval = auto_save_interval
        
        # 加载已有数据
        self._load_from_disk()
    
    def _load_from_disk(self) -> None:
        """
        从磁盘加载记忆数据到内存缓存
        O(1)初始化,仅在构造时调用
        """
        with self._file_lock:
            if not self.memory_file.exists():
                self._memory_cache = {}
                return
            
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 反序列化为MemoryGene对象
                self._memory_cache = {}
                for stock_code, gene_dict in data.items():
                    self._memory_cache[stock_code] = MemoryGene(**gene_dict)
                
                print(f"[MemoryEngine] 已加载 {len(self._memory_cache)} 条记忆记录")
                
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"[MemoryEngine] 加载记忆文件失败: {e}, 初始化空缓存")
                self._memory_cache = {}
    
    def _save_to_disk(self, force: bool = False) -> bool:
        """
        将内存缓存持久化到磁盘
        O(n)写入,n为记忆数量
        
        Args:
            force: 强制写入,忽略脏标记
            
        Returns:
            是否成功写入
        """
        with self._file_lock:
            with self._cache_lock:
                if not force and not self._dirty:
                    return True
                
                try:
                    # 序列化为字典
                    data = {}
                    for stock_code, gene in self._memory_cache.items():
                        data[stock_code] = asdict(gene)
                    
                    # 原子写入: 先写临时文件,再重命名
                    temp_file = self.memory_file.with_suffix('.tmp')
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    # 重命名为正式文件(原子操作)
                    temp_file.replace(self.memory_file)
                    
                    self._dirty = False
                    self._last_save_time = time.time()
                    
                    print(f"[MemoryEngine] 已保存 {len(data)} 条记忆到磁盘")
                    return True
                    
                except Exception as e:
                    print(f"[MemoryEngine] 保存记忆文件失败: {e}")
                    return False
    
    def _check_auto_save(self) -> None:
        """检查并执行自动保存"""
        if self._auto_save:
            elapsed = time.time() - self._last_save_time
            if elapsed > self._auto_save_interval:
                self._save_to_disk()
    
    def _get_today_str(self) -> str:
        """获取今日日期字符串 YYYYMMDD"""
        return datetime.now().strftime('%Y%m%d')
    
    def _is_trading_day_gap(self, date1: str, date2: str) -> int:
        """
        计算两个日期间的交易天数差
        简化实现: 假设每天都是交易日
        
        Args:
            date1: 较早日期 YYYYMMDD
            date2: 较晚日期 YYYYMMDD
            
        Returns:
            交易天数差
        """
        d1 = datetime.strptime(date1, '%Y%m%d')
        d2 = datetime.strptime(date2, '%Y%m%d')
        
        # 计算日历天数差
        calendar_days = (d2 - d1).days
        
        # 简化为交易日: 假设每周5个交易日
        # 实际应从交易日历查询
        trading_days = calendar_days
        
        return max(0, trading_days)
    
    def _should_write_memory(self, gain_pct: float, turnover_rate: float) -> bool:
        """
        判断是否应该写入记忆
        条件: 涨幅>8% 且 换手>5%
        
        Args:
            gain_pct: 涨幅百分比
            turnover_rate: 换手率百分比
            
        Returns:
            是否满足写入条件
        """
        return (gain_pct > self.GAIN_THRESHOLD and 
                turnover_rate > self.TURNOVER_THRESHOLD)
    
    def write_memory(self, 
                     stock_code: str, 
                     gain_pct: float,
                     turnover_rate: float,
                     blood_pct: float,
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        基因写入 - 盘后结算时调用
        
        写入条件: 涨幅>8% 且 换手>5%
        写入内容: blood_pct作为初始当量M0
        
        Args:
            stock_code: 股票代码
            gain_pct: 当日涨幅(%)
            turnover_rate: 当日换手率(%)
            blood_pct: 血液浓度分数(0-100)
            metadata: 额外元数据
            
        Returns:
            是否成功写入
        """
        # 检查写入条件
        if not self._should_write_memory(gain_pct, turnover_rate):
            return False
        
        today = self._get_today_str()
        
        with self._cache_lock:
            # 创建新的记忆基因
            gene = MemoryGene(
                stock_code=stock_code,
                initial_score=blood_pct,
                current_score=blood_pct,  # 初始当量M0
                create_date=today,
                last_active_date=today,
                half_life_count=0,
                metadata={
                    'gain_pct': gain_pct,
                    'turnover_rate': turnover_rate,
                    'write_time': datetime.now().isoformat(),
                    **(metadata or {})
                }
            )
            
            # O(1)写入缓存
            self._memory_cache[stock_code] = gene
            self._dirty = True
        
        print(f"[MemoryEngine] 基因写入: {stock_code} | "
              f"M0={blood_pct:.2f} | 涨幅={gain_pct:.2f}% | 换手={turnover_rate:.2f}%")
        
        self._check_auto_save()
        return True
    
    def read_memory(self, stock_code: str, today: Optional[str] = None) -> Optional[float]:
        """
        半衰期读取 - 次日开盘时调用
        
        读取逻辑:
            1. 查找该股票的记忆基因
            2. 检查是否已衰减过(当日只能衰减一次)
            3. 计算半衰期衰减: current_score *= 0.5^days
            4. 更新last_active_date
            
        Args:
            stock_code: 股票代码
            today: 当前日期(YYYYMMDD),默认今日
            
        Returns:
            衰减后的当量分数,无记忆返回None
        """
        if today is None:
            today = self._get_today_str()
        
        with self._cache_lock:
            gene = self._memory_cache.get(stock_code)
            if gene is None:
                return None
            
            # 检查当日是否已衰减过
            if gene.last_active_date == today:
                # 今日已读取,返回当前值(不再衰减)
                return gene.current_score
            
            # 计算经过的交易日天数
            days_passed = self._is_trading_day_gap(gene.last_active_date, today)
            
            if days_passed <= 0:
                # 同一天,不衰减
                return gene.current_score
            
            # 半衰期衰减: M = M0 * (0.5)^n
            decay_factor = self.HALF_LIFE_FACTOR ** days_passed
            new_score = gene.current_score * decay_factor
            
            # 更新基因
            gene.current_score = new_score
            gene.last_active_date = today
            gene.half_life_count += days_passed
            self._dirty = True
            
            print(f"[MemoryEngine] 半衰期读取: {stock_code} | "
                  f"衰减{days_passed}天 | {gene.current_score/decay_factor:.2f} -> {new_score:.2f}")
            
            return new_score
    
    def read_all_active_memories(self, 
                                  today: Optional[str] = None) -> Dict[str, float]:
        """
        批量读取所有活跃记忆
        
        Args:
            today: 当前日期,默认今日
            
        Returns:
            {stock_code: decayed_score} 字典
        """
        if today is None:
            today = self._get_today_str()
        
        result = {}
        # 必须在锁外调用read_memory避免死锁
        stock_codes = []
        with self._cache_lock:
            stock_codes = list(self._memory_cache.keys())
        
        for stock_code in stock_codes:
            score = self.read_memory(stock_code, today)
            if score is not None:
                result[stock_code] = score
        
        return result
    
    def annihilate_expired(self, 
                          today: Optional[str] = None,
                          dry_run: bool = False) -> List[str]:
        """
        TTL湮灭 - 清理过期记忆
        
        湮灭条件: last_active_date距today ≥ TTL_DAYS个交易日
        
        Args:
            today: 当前日期,默认今日
            dry_run: 只返回待删除列表,不实际删除
            
        Returns:
            被湮灭的股票代码列表
        """
        if today is None:
            today = self._get_today_str()
        
        to_annihilate = []
        
        with self._cache_lock:
            for stock_code, gene in list(self._memory_cache.items()):
                days_inactive = self._is_trading_day_gap(gene.last_active_date, today)
                
                if days_inactive >= self.TTL_DAYS:
                    to_annihilate.append(stock_code)
            
            if not dry_run:
                for stock_code in to_annihilate:
                    del self._memory_cache[stock_code]
                
                if to_annihilate:
                    self._dirty = True
        
        if to_annihilate:
            mode_str = "[模拟]" if dry_run else ""
            print(f"[MemoryEngine] {mode_str}TTL湮灭: {len(to_annihilate)}条记忆被清除")
            for code in to_annihilate[:5]:  # 只显示前5条
                print(f"  - {code}")
            if len(to_annihilate) > 5:
                print(f"  ... 等共{len(to_annihilate)}条")
        
        return to_annihilate
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        Returns:
            统计信息字典
        """
        with self._cache_lock:
            total = len(self._memory_cache)
            if total == 0:
                return {
                    'total_memories': 0,
                    'avg_score': 0.0,
                    'max_score': 0.0,
                    'min_score': 0.0
                }
            
            scores = [g.current_score for g in self._memory_cache.values()]
            
            return {
                'total_memories': total,
                'avg_score': sum(scores) / total,
                'max_score': max(scores),
                'min_score': min(scores),
                'half_life_total': sum(g.half_life_count for g in self._memory_cache.values())
            }
    
    def has_memory(self, stock_code: str) -> bool:
        """检查是否有某股票的记忆"""
        with self._cache_lock:
            return stock_code in self._memory_cache
    
    def get_memory_detail(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取某股票的记忆详情"""
        with self._cache_lock:
            gene = self._memory_cache.get(stock_code)
            if gene:
                return asdict(gene)
            return None
    
    def force_save(self) -> bool:
        """强制立即保存到磁盘"""
        return self._save_to_disk(force=True)
    
    def clear_all(self, confirm: bool = False) -> bool:
        """
        清空所有记忆(危险操作)
        
        Args:
            confirm: 必须传入True才能执行
            
        Returns:
            是否成功清空
        """
        if not confirm:
            print("[MemoryEngine] 清空操作被拒绝: confirm=True才能执行")
            return False
        
        with self._cache_lock:
            self._memory_cache.clear()
            self._dirty = True
        
        self._save_to_disk(force=True)
        print("[MemoryEngine] 所有记忆已清空")
        return True
    
    def close(self):
        """关闭引擎,保存数据"""
        self._save_to_disk(force=True)
        print("[MemoryEngine] 引擎已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口,自动保存"""
        self.close()


# =============================================================================
# 使用示例
# =============================================================================

def example_usage():
    """
    ShortTermMemoryEngine 使用示例
    
    场景模拟:
        Day 0 (20260225): 盘后结算,3只股票触发写入
        Day 1 (20260226): 开盘读取,记忆衰减0.5倍
        Day 2 (20260227): 开盘读取,记忆再衰减0.5倍
        Day 3 (20260228): 湮灭过期记忆(≥2天未激活)
    """
    print("=" * 60)
    print("ShortTermMemoryEngine 使用示例")
    print("=" * 60)
    
    # 使用临时文件进行测试
    test_file = "data/memory/test_short_term_memory.json"
    
    # 清理测试文件
    if os.path.exists(test_file):
        os.remove(test_file)
    
    # 固定测试日期
    DAY0 = "20260225"
    DAY1 = "20260226"
    DAY2 = "20260227"
    DAY3 = "20260228"
    DAY4 = "20260301"
    
    # -------------------------------------------------------------------------
    # Day 0: 盘后结算 - 基因写入
    # -------------------------------------------------------------------------
    print(f"\n>>> Day 0 ({DAY0}) 盘后结算 - 基因写入")
    
    engine = ShortTermMemoryEngine(memory_file=test_file, auto_save=False)
    
    # 手动创建记忆基因(绕过write_memory的日期自动获取)
    from datetime import datetime
    
    def create_test_gene(stock_code, blood_pct, gain_pct, turnover_rate, date_str):
        """创建测试记忆基因"""
        gene = MemoryGene(
            stock_code=stock_code,
            initial_score=blood_pct,
            current_score=blood_pct,
            create_date=date_str,
            last_active_date=date_str,
            half_life_count=0,
            metadata={
                'gain_pct': gain_pct,
                'turnover_rate': turnover_rate,
                'write_time': datetime.now().isoformat()
            }
        )
        return gene
    
    # 股票A: 强势涨停,写入记忆
    engine._memory_cache["000001.SZ"] = create_test_gene(
        "000001.SZ", 92.0, 10.02, 8.5, DAY0
    )
    print(f"[MemoryEngine] 基因写入: 000001.SZ | M0=92.00 | 涨幅=10.02% | 换手=8.50%")
    
    # 股票B: 强势但未达标(<8%),不写入
    # gain_pct=7.5不满足>8%条件,跳过
    print(f"[MemoryEngine] 条件未满足: 000002.SZ | 涨幅=7.50% (<8%) | 跳过")
    
    # 股票C: 达标,写入记忆
    engine._memory_cache["300001.SZ"] = create_test_gene(
        "300001.SZ", 88.5, 19.8, 25.6, DAY0
    )
    print(f"[MemoryEngine] 基因写入: 300001.SZ | M0=88.50 | 涨幅=19.80% | 换手=25.60%")
    
    # 股票D: 达标,写入记忆
    engine._memory_cache["600000.SH"] = create_test_gene(
        "600000.SH", 78.0, 9.5, 6.2, DAY0
    )
    print(f"[MemoryEngine] 基因写入: 600000.SH | M0=78.00 | 涨幅=9.50% | 换手=6.20%")
    
    engine._dirty = True
    stats = engine.get_memory_stats()
    print(f"\n当日记忆统计: {stats}")
    engine.force_save()
    
    # -------------------------------------------------------------------------
    # Day 1: 次日开盘 - 半衰期读取
    # -------------------------------------------------------------------------
    print(f"\n>>> Day 1 ({DAY1}) 开盘 - 半衰期读取")
    
    # 重新加载引擎(模拟次日重启)
    engine = ShortTermMemoryEngine(memory_file=test_file, auto_save=False)
    
    # 读取所有活跃记忆
    memories = engine.read_all_active_memories(today=DAY1)
    
    print("\n衰减后的记忆当量:")
    for code, score in memories.items():
        detail = engine.get_memory_detail(code)
        half_life = detail['half_life_count']
        m0 = detail['initial_score']
        decay_factor = 0.5 ** half_life
        print(f"  {code}: M0={m0:.2f} -> M1={score:.2f} "
              f"(衰减{half_life}天, 衰减系数{decay_factor:.2f})")
    
    # -------------------------------------------------------------------------
    # Day 2: 再次开盘 - 再次衰减
    # -------------------------------------------------------------------------
    print(f"\n>>> Day 2 ({DAY2}) 开盘 - 再次半衰期读取")
    
    memories = engine.read_all_active_memories(today=DAY2)
    
    print("\n二次衰减后的记忆当量:")
    for code, score in memories.items():
        detail = engine.get_memory_detail(code)
        half_life = detail['half_life_count']
        m0 = detail['initial_score']
        decay_factor = 0.5 ** half_life
        print(f"  {code}: M0={m0:.2f} -> M2={score:.2f} "
              f"(衰减{half_life}天, 衰减系数{decay_factor:.2f})")
    
    # -------------------------------------------------------------------------
    # Day 4: TTL湮灭 - 清理过期记忆(≥2天未激活)
    # -------------------------------------------------------------------------
    print(f"\n>>> Day 4 ({DAY4}) - TTL湮灭检查")
    print(f"    (自{DAY2}以来≥2天未激活,触发湮灭)")
    
    # 模拟湮灭(dry_run)
    expired = engine.annihilate_expired(today=DAY4, dry_run=True)
    print(f"\n待湮灭记录: {len(expired)}条")
    
    # 实际湮灭
    expired = engine.annihilate_expired(today=DAY4, dry_run=False)
    
    stats = engine.get_memory_stats()
    print(f"\n湮灭后记忆统计: {stats}")
    
    # -------------------------------------------------------------------------
    # 清理
    # -------------------------------------------------------------------------
    engine.close()
    
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"\n测试文件已清理: {test_file}")
    
    print("\n" + "=" * 60)
    print("示例执行完毕")
    print("=" * 60)



if __name__ == "__main__":
    example_usage()
