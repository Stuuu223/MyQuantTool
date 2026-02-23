# -*- coding: utf-8 -*-
"""
股票池构建器 V2.0 - CTO Phase 6.2 重构版

职责：
1. Tushare云端三层漏斗筛选（5000→200）
2. 顽主精选股票池构建
3. 统一的股票池构建接口

重构目标：
- 整合 tasks/tushare_market_filter.py
- 提供模块化API接口
- 完整错误处理和类型注解

三层漏斗架构：
- Layer 1: 静态过滤（ST/北交所/停牌）
- Layer 2: 成交额过滤（5日日均>3000万）
- Layer 3: 量比过滤（量比>3，取Top200）

使用示例:
    >>> from logic.analyzers.universe_builder import UniverseBuilder
    >>> builder = UniverseBuilder()
    >>> universe_df = builder.build_universe(trade_date='20251231')
    >>> top_73 = builder.get_top_candidates(n=73)
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

import pandas as pd

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    ts = None

from logic.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FilterResult:
    """过滤结果数据结构"""
    layer: int
    name: str
    input_count: int
    output_count: int
    duration_ms: float
    params: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def filter_ratio(self) -> float:
        """过滤比率 (0.0-1.0)"""
        if self.input_count == 0:
            return 0.0
        return 1 - (self.output_count / self.input_count)
    
    def __str__(self) -> str:
        return (f"Layer {self.layer} [{self.name}]: "
                f"{self.input_count} → {self.output_count} "
                f"(过滤 {self.filter_ratio*100:.1f}%)")


@dataclass
class UniverseBuildReport:
    """股票池构建报告"""
    trade_date: str
    total_stocks: int
    final_count: int
    filter_results: List[FilterResult] = field(default_factory=list)
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'trade_date': self.trade_date,
            'total_stocks': self.total_stocks,
            'final_count': self.final_count,
            'duration_seconds': self.duration_seconds,
            'filters': [
                {
                    'layer': f.layer,
                    'name': f.name,
                    'input': f.input_count,
                    'output': f.output_count,
                    'filter_ratio': f.filter_ratio
                }
                for f in self.filter_results
            ]
        }


class UniverseBuilder:
    """
    股票池构建器（Tushare三层漏斗）
    
    整合Tushare云端粗筛能力，提供标准化的股票池构建流程。
    
    Attributes:
        tushare_token: Tushare API Token
        min_avg_amount: 5日平均成交额阈值（万元）
        volume_ratio_threshold: 量比阈值
        max_output: 最大输出数量
        api_delay: API调用间隔（秒）
    
    Example:
        >>> builder = UniverseBuilder(tushare_token="your_token")
        >>> df = builder.build_universe('20251231')
        >>> print(f"筛选结果: {len(df)}只股票")
    """
    
    # 默认配置（从CTO配置中提取）
    DEFAULT_MIN_AVG_AMOUNT = 3000  # 万元
    DEFAULT_VOLUME_RATIO_THRESHOLD = 3.0
    DEFAULT_MAX_OUTPUT = 200
    DEFAULT_API_DELAY = 0.5
    DEFAULT_TUSHARE_TOKEN = '1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b'
    
    def __init__(
        self,
        tushare_token: Optional[str] = None,
        min_avg_amount: float = DEFAULT_MIN_AVG_AMOUNT,
        volume_ratio_threshold: float = DEFAULT_VOLUME_RATIO_THRESHOLD,
        max_output: int = DEFAULT_MAX_OUTPUT,
        api_delay: float = DEFAULT_API_DELAY
    ):
        """
        初始化股票池构建器
        
        Args:
            tushare_token: Tushare API Token
            min_avg_amount: 5日平均成交额阈值（万元）
            volume_ratio_threshold: 量比阈值
            max_output: 最大输出数量
            api_delay: API调用间隔（秒）
        """
        self.tushare_token = tushare_token or self._load_tushare_token()
        self.min_avg_amount = min_avg_amount
        self.volume_ratio_threshold = volume_ratio_threshold
        self.max_output = max_output
        self.api_delay = api_delay
        self._pro = None
        self._filter_results: List[FilterResult] = []
        self._last_result: Optional[pd.DataFrame] = None
        
        logger.info(f"[UniverseBuilder] 初始化完成 | 成交额>{min_avg_amount}万 | 量比>{volume_ratio_threshold}")
    
    def _load_tushare_token(self) -> str:
        """从配置文件加载Tushare Token"""
        try:
            token_file = Path(__file__).parent.parent.parent / 'config' / 'tushare_token.txt'
            if token_file.exists():
                token = token_file.read_text().strip()
                if token and not token.startswith('替换'):
                    return token
        except Exception as e:
            logger.warning(f"[UniverseBuilder] 加载Token文件失败: {e}")
        
        logger.info("[UniverseBuilder] 使用默认Tushare Token")
        return self.DEFAULT_TUSHARE_TOKEN
    
    def init_tushare(self) -> bool:
        """
        初始化Tushare Pro API
        
        Returns:
            是否初始化成功
        """
        if not TUSHARE_AVAILABLE:
            logger.error("[UniverseBuilder] tushare模块未安装")
            return False
        
        if self._pro is not None:
            return True
        
        try:
            ts.set_token(self.tushare_token)
            self._pro = ts.pro_api()
            logger.info("[UniverseBuilder] Tushare Pro初始化成功")
            return True
        except Exception as e:
            logger.error(f"[UniverseBuilder] Tushare Pro初始化失败: {e}")
            return False
    
    def _get_trade_dates(self, end_date: str, days: int = 5) -> List[str]:
        """
        获取历史交易日列表
        
        Args:
            end_date: 结束日期 (YYYYMMDD)
            days: 需要获取的交易日数量
        
        Returns:
            交易日列表（从旧到新）
        """
        try:
            # 使用trade_cal接口获取交易日历
            df = self._pro.trade_cal(
                end_date=end_date,
                is_open='1',
                fields='cal_date'
            )
            if df is None or df.empty:
                # 降级：使用简单日期计算
                return self._calc_trade_dates_fallback(end_date, days)
            
            dates = df['cal_date'].tolist()
            dates.sort()
            return dates[-days:] if len(dates) >= days else dates
            
        except Exception as e:
            logger.warning(f"[UniverseBuilder] 获取交易日历失败: {e}，使用降级方案")
            return self._calc_trade_dates_fallback(end_date, days)
    
    def _calc_trade_dates_fallback(self, end_date: str, days: int) -> List[str]:
        """交易日历降级计算（排除周末）"""
        date_obj = datetime.strptime(end_date, '%Y%m%d')
        dates = []
        
        for i in range(1, 20):  # 最多往前找20天
            d = date_obj - timedelta(days=i)
            d_str = d.strftime('%Y%m%d')
            if d.weekday() < 5:  # 0-4是周一到周五
                dates.append(d_str)
            if len(dates) >= days:
                break
        
        dates.sort()
        return dates
    
    def filter_layer1_static(self, df_base: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Layer 1: 静态过滤（5000→约4500）
        
        过滤规则：
        - 剔除ST/*ST/退市
        - 剔除北交所（8/4开头）
        - 只保留上市状态为'L'的股票
        
        Args:
            df_base: 基础股票列表，None时自动获取
        
        Returns:
            过滤后的DataFrame
        """
        start_time = time.time()
        
        if not self.init_tushare():
            raise RuntimeError("Tushare未初始化")
        
        logger.info("=" * 60)
        logger.info("【Layer 1】Tushare静态过滤")
        logger.info("=" * 60)
        
        if df_base is not None:
            df = df_base.copy()
            input_count = len(df)
        else:
            # 获取全市场股票基础信息
            df = self._pro.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol,name,area,industry,list_date'
            )
            input_count = len(df)
        
        logger.info(f"   全市场股票总数: {len(df)}")
        
        # 剔除北交所（8/4开头）
        df = df[~df['ts_code'].str.startswith(('8', '4'))]
        logger.info(f"   剔除北交所后: {len(df)}")
        
        # 剔除ST（名称中包含ST）
        df = df[~df['name'].str.contains('ST', na=False)]
        logger.info(f"   剔除ST后: {len(df)}")
        
        duration = (time.time() - start_time) * 1000
        result = FilterResult(
            layer=1,
            name='静态过滤',
            input_count=input_count,
            output_count=len(df),
            duration_ms=duration
        )
        self._filter_results.append(result)
        logger.info(f"   {result}")
        
        return df
    
    def filter_layer2_amount(
        self,
        df_base: pd.DataFrame,
        trade_date: str
    ) -> pd.DataFrame:
        """
        Layer 2: 成交额过滤（约4500→约800）
        
        过滤规则：
        - 计算前5日日均成交额
        - 剔除<3000万的股票
        
        Args:
            df_base: 基础股票DataFrame
            trade_date: 交易日期 (YYYYMMDD)
        
        Returns:
            过滤后的DataFrame
        """
        start_time = time.time()
        
        if not self.init_tushare():
            raise RuntimeError("Tushare未初始化")
        
        logger.info("=" * 60)
        logger.info("【Layer 2】Tushare成交额过滤")
        logger.info("=" * 60)
        
        # 计算前5个交易日
        dates = self._get_trade_dates(trade_date, 5)
        logger.info(f"   分析日期范围: {dates[0]} 至 {dates[-1]}")
        
        # 批量获取日线数据
        all_daily = []
        for date in dates:
            try:
                df_daily = self._pro.daily(trade_date=date, fields='ts_code,amount')
                if df_daily is not None and not df_daily.empty:
                    all_daily.append(df_daily)
                    logger.debug(f"   ✅ {date}: {len(df_daily)}只")
                time.sleep(self.api_delay)
            except Exception as e:
                logger.warning(f"   ❌ {date}: {e}")
        
        if not all_daily:
            raise ValueError("无法获取历史日线数据")
        
        # 合并并计算5日平均成交额
        df_all = pd.concat(all_daily, ignore_index=True)
        df_avg = df_all.groupby('ts_code')['amount'].mean().reset_index()
        df_avg.columns = ['ts_code', 'avg_amount_5d']
        
        # 合并到基础数据
        df = df_base.merge(df_avg, on='ts_code', how='inner')
        
        # 过滤：日均成交额>3000万（Tushare amount单位是千元，所以3000万=30000千元）
        threshold_k = self.min_avg_amount * 10
        df_filtered = df[df['avg_amount_5d'] >= threshold_k].copy()
        
        duration = (time.time() - start_time) * 1000
        result = FilterResult(
            layer=2,
            name='成交额过滤',
            input_count=len(df_base),
            output_count=len(df_filtered),
            duration_ms=duration,
            params={'min_amount': self.min_avg_amount}
        )
        self._filter_results.append(result)
        logger.info(f"   5日日均成交>{self.min_avg_amount}万: {len(df_filtered)}只")
        logger.info(f"   {result}")
        
        return df_filtered
    
    def filter_layer3_volume_ratio(
        self,
        df_base: pd.DataFrame,
        trade_date: str
    ) -> pd.DataFrame:
        """
        Layer 3: 量比过滤（约800→200）
        
        过滤规则：
        - 获取当日量比数据
        - 保留量比>3的股票
        - 按量比排序，取Top N
        
        Args:
            df_base: 基础股票DataFrame
            trade_date: 交易日期 (YYYYMMDD)
        
        Returns:
            过滤后的DataFrame
        """
        start_time = time.time()
        
        if not self.init_tushare():
            raise RuntimeError("Tushare未初始化")
        
        logger.info("=" * 60)
        logger.info("【Layer 3】Tushare量比过滤")
        logger.info("=" * 60)
        
        # 获取当日指标数据
        try:
            df_today = self._pro.daily_basic(
                trade_date=trade_date,
                fields='ts_code,turnover_rate,volume_ratio'
            )
            logger.info(f"   获取当日指标: {len(df_today)}只")
        except Exception as e:
            logger.error(f"   获取当日指标失败: {e}")
            # 降级：直接返回前N只
            df_fallback = df_base.head(self.max_output).copy()
            df_fallback['volume_ratio'] = None
            return df_fallback
        
        # 合并数据
        df = df_base.merge(df_today, on='ts_code', how='inner')
        
        # 过滤：量比>阈值
        df_filtered = df[df['volume_ratio'] >= self.volume_ratio_threshold].copy()
        logger.info(f"   量比>{self.volume_ratio_threshold}: {len(df_filtered)}只")
        
        # 按量比排序，取前N
        df_filtered = df_filtered.sort_values('volume_ratio', ascending=False)
        df_result = df_filtered.head(self.max_output).copy()
        
        duration = (time.time() - start_time) * 1000
        result = FilterResult(
            layer=3,
            name='量比过滤',
            input_count=len(df_base),
            output_count=len(df_result),
            duration_ms=duration,
            params={'volume_ratio_threshold': self.volume_ratio_threshold, 'max_output': self.max_output}
        )
        self._filter_results.append(result)
        logger.info(f"   Top {self.max_output}: {len(df_result)}只")
        logger.info(f"   {result}")
        
        return df_result
    
    def build_universe(
        self,
        trade_date: Optional[str] = None,
        df_base: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        执行三层漏斗完整筛选
        
        Args:
            trade_date: 交易日期 (YYYYMMDD)，默认今天
            df_base: 基础股票列表，None时自动获取
        
        Returns:
            筛选结果DataFrame
        """
        start_time = time.time()
        self._filter_results = []
        
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        logger.info("=" * 60)
        logger.info("【股票池构建】三层漏斗筛选")
        logger.info("=" * 60)
        logger.info(f"目标日期: {trade_date}")
        logger.info(f"成交额底线: {self.min_avg_amount}万")
        logger.info(f"量比阈值: {self.volume_ratio_threshold}")
        logger.info("=" * 60)
        
        if not self.init_tushare():
            raise RuntimeError("Tushare初始化失败")
        
        # Layer 1: 静态过滤
        df = self.filter_layer1_static(df_base)
        
        # Layer 2: 成交额过滤
        df = self.filter_layer2_amount(df, trade_date)
        
        # Layer 3: 量比过滤
        df = self.filter_layer3_volume_ratio(df, trade_date)
        
        # 添加排名列
        df['rank'] = range(1, len(df) + 1)
        
        self._last_result = df
        duration = time.time() - start_time
        
        logger.info("=" * 60)
        logger.info("【筛选结果摘要】")
        logger.info("=" * 60)
        logger.info(f"最终入选: {len(df)}只")
        logger.info(f"耗时: {duration:.2f}秒")
        
        return df
    
    def get_top_candidates(self, n: int = 73) -> List[str]:
        """
        获取Top N候选股票代码
        
        Args:
            n: 获取数量
        
        Returns:
            股票代码列表
        """
        if self._last_result is None or self._last_result.empty:
            logger.warning("[UniverseBuilder] 没有可用的筛选结果")
            return []
        
        return self._last_result.head(n)['ts_code'].tolist()
    
    def get_build_report(self) -> UniverseBuildReport:
        """
        获取构建报告
        
        Returns:
            构建报告对象
        """
        if not self._filter_results:
            return UniverseBuildReport(
                trade_date='',
                total_stocks=0,
                final_count=0
            )
        
        first_filter = self._filter_results[0]
        last_filter = self._filter_results[-1]
        
        return UniverseBuildReport(
            trade_date=datetime.now().strftime('%Y%m%d'),
            total_stocks=first_filter.input_count,
            final_count=last_filter.output_count,
            filter_results=self._filter_results
        )
    
    def save_universe(
        self,
        df: Optional[pd.DataFrame] = None,
        output_dir: Optional[Path] = None,
        trade_date: Optional[str] = None,
        format: str = 'both'
    ) -> Dict[str, Path]:
        """
        保存股票池到文件
        
        Args:
            df: 要保存的DataFrame，None使用最后一次结果
            output_dir: 输出目录
            trade_date: 交易日期
            format: 格式 ('csv', 'json', 'both')
        
        Returns:
            保存的文件路径字典
        """
        if df is None:
            df = self._last_result
        
        if df is None or df.empty:
            logger.warning("[UniverseBuilder] 没有数据可保存")
            return {}
        
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / 'data' / 'scan_results'
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        saved_files = {}
        base_name = f"{trade_date}_candidates_{len(df)}"
        
        # 保存CSV
        if format in ('csv', 'both'):
            csv_path = output_dir / f"{base_name}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            saved_files['csv'] = csv_path
            logger.info(f"💾 已保存CSV: {csv_path}")
        
        # 保存JSON
        if format in ('json', 'both'):
            json_path = output_dir / f"{base_name}.json"
            df.to_json(json_path, orient='records', force_ascii=False, indent=2)
            saved_files['json'] = json_path
            logger.info(f"💾 已保存JSON: {json_path}")
        
        return saved_files
    
    def check_specific_stock(self, ts_code: str) -> Optional[Dict]:
        """
        检查特定股票是否在最后一次筛选结果中
        
        Args:
            ts_code: 股票代码
        
        Returns:
            股票信息字典，未找到返回None
        """
        if self._last_result is None or self._last_result.empty:
            return None
        
        stock = self._last_result[self._last_result['ts_code'] == ts_code]
        if stock.empty:
            return None
        
        row = stock.iloc[0]
        return {
            'ts_code': row['ts_code'],
            'name': row.get('name', ''),
            'rank': int(row.get('rank', 0)),
            'volume_ratio': float(row.get('volume_ratio', 0)),
            'avg_amount_5d': float(row.get('avg_amount_5d', 0))
        }


# ==========================================
# 保留原有功能：顽主精选股票池
# ==========================================

def load_json_config(config_path: Path) -> Dict:
    """加载JSON配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_stock_code(code: str) -> tuple:
    """解析股票代码
    
    Args:
        code: 原始代码（如 '600519.SH' 或 '600519'）
    
    Returns:
        (qmt_code, market, full_code)
    """
    if code.endswith('.SH'):
        return code[:-3], 'SH', code
    elif code.endswith('.SZ'):
        return code[:-3], 'SZ', code
    elif code.startswith('6'):
        return code, 'SH', f"{code}.SH"
    elif code.startswith('0') or code.startswith('3'):
        return code, 'SZ', f"{code}.SZ"
    else:
        return code, 'UNKNOWN', code


def build_wanzhu_selected() -> List[Dict]:
    """构建顽主精选150股票池（从CSV）
    
    从 data/wanzhu_data/processed/wanzhu_selected_150.csv 读取
    
    Returns:
        标准化股票列表
    """
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    csv_path = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'
    
    if not csv_path.exists():
        raise FileNotFoundError(f"找不到CSV文件: {csv_path}")
    
    df = pd.read_csv(csv_path)
    stocks = []
    
    for idx, row in df.iterrows():
        code = str(row['code']).zfill(6)
        qmt_code, market, full_code = parse_stock_code(code)
        
        stocks.append({
            "code": full_code,
            "qmt_code": qmt_code,
            "market": market,
            "name": row.get('name', ''),
            "rank": idx + 1,
            "source": "wanzhu_selected"
        })
    
    return stocks


def save_universe_legacy(universe: List[Dict], output_path: Path, format: str = 'json'):
    """保存股票池到文件（旧版兼容）
    
    Args:
        universe: 股票列表
        output_path: 输出路径
        format: 格式 ('json' 或 'csv')
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'json':
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(universe, f, ensure_ascii=False, indent=2)
    elif format == 'csv':
        df = pd.DataFrame(universe)
        df.to_csv(output_path, index=False, encoding='utf-8')
    else:
        raise ValueError(f"不支持的格式: {format}")
    
    logger.info(f"✅ 股票池已保存: {output_path}")
    logger.info(f"   股票数量: {len(universe)}")


def get_universe_summary(universe: List[Dict]) -> Dict:
    """获取股票池摘要统计
    
    Args:
        universe: 股票列表
    
    Returns:
        统计信息字典
    """
    sh_count = sum(1 for s in universe if s['market'] == 'SH')
    sz_count = sum(1 for s in universe if s['market'] == 'SZ')
    
    sources = {}
    for s in universe:
        src = s.get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1
    
    return {
        'total': len(universe),
        'sh_count': sh_count,
        'sz_count': sz_count,
        'sources': sources
    }


if __name__ == '__main__':
    # 测试构建
    print("=" * 60)
    print("股票池构建器 V2.0 测试")
    print("=" * 60)
    
    # 测试 Tushare 三层漏斗
    print("\n测试 Tushare 三层漏斗...")
    try:
        builder = UniverseBuilder()
        df = builder.build_universe('20251231')
        top_10 = builder.get_top_candidates(n=10)
        print(f"\nTop 10候选:")
        for code in top_10:
            print(f"   {code}")
        
        # 检查志特新材
        zhite = builder.check_specific_stock('300986.SZ')
        if zhite:
            print(f"\n🎯 志特新材(300986.SZ): 排名 {zhite['rank']}, 量比 {zhite['volume_ratio']:.2f}")
        else:
            print(f"\n志特新材(300986.SZ): 未入选")
            
    except Exception as e:
        print(f"Tushare测试失败: {e}")
    
    # 测试顽主精选
    print("\n" + "=" * 60)
    print("测试顽主精选...")
    try:
        universe = build_wanzhu_selected()
        summary = get_universe_summary(universe)
        print(f"  总数: {summary['total']}")
        print(f"  上海: {summary['sh_count']}, 深圳: {summary['sz_count']}")
        print(f"  来源: {summary['sources']}")
        print("\n前5只股票:")
        for s in universe[:5]:
            print(f"  {s['rank']:3d}. {s['name']} ({s['code']})")
    except Exception as e:
        print(f"顽主精选测试失败: {e}")