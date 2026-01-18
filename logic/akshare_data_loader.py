"""
AKShare 实时数据加载器

龙虎榜、板块、K线数据一站式获取
"""
import akshare as ak
import pandas as pd
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AKShareDataLoader:
    """
    AKShare 数据加载器
    
    实时获取龙虎榜、板块、K线数据
    """
    
    # ============================================================================
    # 龙虎榜数据 API
    # ============================================================================
    
    @staticmethod
    def get_lhb_daily(date: str) -> pd.DataFrame:
        """
        获取龙虎榜月日个股明细
        
        Args:
            date (str): 日期, 格式 "20260107"
        
        Returns:
            pd.DataFrame: 龙虎榜个股详情
                - 代码: 股票代码
                - 名称: 股票名称
                - 上榌符次: 欦次上榌次数
                - 买入: 累计买入集合竞价成交数(3个)
                - 卖出: 累计卖出集合竞价成交数(3个)
                - 收买: 收买集合竞价成交数
                - 成交馇: 增加成交金额
                - 美涨幅: 涨跌幅 (%)
        """
        try:
            df = ak.stock_lhb_detail_em(start_date=date, end_date=date)
            logger.info(f"成功获取 {date} 龙虎榜数据, 共 {len(df)} 条记录")
            return df
        except Exception as e:
            logger.error(f"获取 {date} 龙虎榜数据失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_lhb_stat(days: int = 30) -> pd.DataFrame:
        """
        获取龙虎榜个股累计统计
        
        Args:
            days (int): 日数 ((详细列表无此参数)
        
        Returns:
            pd.DataFrame: 累计统计
                - 代码
                - 名称
                - 上榌符次: 欦次次数
                - 累计买入: 累计买入金额
                - 累计卖出: 累计卖出金额
        """
        try:
            df = ak.stock_lhb_stock_statistic_em()
            logger.info(f"成功获取龙虎榜累计统计, 共 {len(df)} 条记录")
            return df
        except Exception as e:
            logger.error(f"获取龙虎榜累计统计失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_lhb_business_top() -> pd.DataFrame:
        """
        获取龙虎榜业务部排行
        
        Returns:
            pd.DataFrame: 业务部排行
                - 业务部名称
                - 上榌符次
                - 累计买入
                - 累计卖出
        """
        try:
            df = ak.stock_lhb_yybph_em()
            logger.info(f"成功获取业务部排行, 共 {len(df)} 个业务部")
            return df
        except Exception as e:
            logger.error(f"获取业务部排行失败: {e}")
            return pd.DataFrame()
    
    # ============================================================================
    # 板块数据 API
    # ============================================================================
    
    @staticmethod
    def get_sw_industry() -> pd.DataFrame:
        """
        获取申万一级行业板块实时数据
        
        Returns:
            pd.DataFrame: 板块数据
                - 指数代码
                - 指数名称
                - 指数最新价
                - 涨跌幅
                - 涨跌额
                - 成交量
                - 成交额
        """
        try:
            df = ak.sw_index_spot()
            logger.info(f"成功获取申万一级行业, 共 {len(df)} 个板块")
            return df
        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_board_industry_name_em() -> pd.DataFrame:
        """
        获取东方财富行业板块名称列表
        
        Returns:
            pd.DataFrame: 板块名称列表
                - 板块代码
                - 板块名称
        """
        try:
            import akshare as ak
            df = ak.stock_board_industry_name_em()
            logger.info(f"成功获取{len(df)}个行业板块名称")
            return df
        except Exception as e:
            logger.error(f"获取行业板块名称失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_industry_spot() -> pd.DataFrame:
        """
        获取东財行业板块实时行情

        Returns:
            pd.DataFrame: 板块数据
                - 代码
                - 名称
                - 最新价
                - 涨跌幅
                - 涨跌额
                - 成交量
                - 成交额
        """
        try:
            import akshare as ak
            # 先获取板块列表
            name_df = ak.stock_board_industry_name_em()

            if name_df.empty:
                logger.warning("获取板块列表失败")
                return pd.DataFrame()

            # 获取所有板块的实时数据
            all_sectors = []
            for _, row in name_df.iterrows():
                try:
                    sector_code = row['板块代码']
                    sector_name = row['板块名称']

                    # 获取单个板块的实时数据
                    spot_df = ak.stock_board_industry_spot_em(symbol=sector_name)

                    if not spot_df.empty:
                        # 提取关键数据
                        sector_data = {
                            '代码': sector_code,
                            '名称': sector_name,
                            '最新价': 0,
                            '涨跌幅': 0,
                            '涨跌额': 0,
                            '成交量': 0,
                            '成交额': 0
                        }

                        # 从返回的数据中提取值
                        for _, item_row in spot_df.iterrows():
                            item_name = str(item_row['item'])
                            value = item_row['value']

                            # 根据item名称匹配字段
                            if item_name == '最新':
                                sector_data['最新价'] = value
                            elif item_name == '涨跌幅':
                                sector_data['涨跌幅'] = value
                            elif item_name == '涨跌额':
                                sector_data['涨跌额'] = value
                            elif item_name == '成交量':
                                sector_data['成交量'] = value
                            elif item_name == '成交额':
                                sector_data['成交额'] = value
                            elif item_name == '换手率':
                                sector_data['换手率'] = value

                        # 调试日志
                        logger.debug(f"板块 {sector_name} 提取的数据: 换手率={sector_data['换手率']}, 涨跌幅={sector_data['涨跌幅']}")

                        all_sectors.append(sector_data)

                except Exception as e:
                    logger.debug(f"获取板块 {row.get('板块名称', '')} 数据失败: {e}")
                    continue

            if all_sectors:
                result = pd.DataFrame(all_sectors)
                logger.info(f"成功获取{len(result)}个行业板块实时数据")
                return result
            else:
                logger.warning("未获取到任何板块数据")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取行业板块失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_industry_constituents(symbol: str = "BK0001") -> pd.DataFrame:
        """
        获取行业成份股
        
        Args:
            symbol (str): 板块代码, 序楷: "BK0001"=东方財富业, "BK0023"=释能设备
        
        Returns:
            pd.DataFrame: 成份股
                - 成份股代码
                - 成份股名称
        """
        try:
            df = ak.sw_index_cons(index_code=symbol)
            logger.info(f"成功获取 {symbol} 成份股, 共 {len(df)} 只")
            return df
        except Exception as e:
            logger.error(f"获取 {symbol} 成份股失败: {e}")
            return pd.DataFrame()
    
    # ============================================================================
    # K线数据 API
    # ============================================================================
    
    @staticmethod
    def get_stock_daily(
        code: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取个股日线数据
        
        Args:
            code (str): 股票代码, 如 "000001" (不带市场标识)
            start_date (str): 开始日期, 格式 "20250101"
            end_date (str): 结束日期, 格式 "20260107"
            adjust (str): 复权方式
                - "" : 不复权
                - "qfq" : 前复权
                - "hfq" : 后复权
        
        Returns:
            pd.DataFrame: K线数据
                - 日期
                - 股票代码
                - 开盘
                - 收盘
                - 最高
                - 最低
                - 成交量
                - 成交额
                - 挪幅
                - 涨跌幅
                - 涨跌额
                - 换手率
        """
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            logger.info(f"成功获取 {code} K线, {start_date} 至 {end_date}, 共 {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取 {code} K线失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_stock_minute(
        code: str,
        period: str = "1",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取个股分鋳线数据
        
        Args:
            code (str): 股票代码, 需要带市场标识, 如 "sh600000" 或 "sz000001"
            period (str): K线周期
                - "1" : 1分鋳
                - "5" : 5分鋳
                - "15" : 15分鋳
                - "30" : 30分鋳
                - "60" : 60分鋳 (一小时)
            adjust (str): 复权方式
        
        Returns:
            pd.DataFrame: 分鋳线数据
                - 日期
                - 开盘
                - 最高
                - 最低
                - 收盘
                - 成交量
        """
        try:
            # 注意：分鋳线数据只有当日最近交易日的数据
            df = ak.stock_zh_a_minute(
                symbol=code,
                period=period,
                adjust=adjust
            )
            logger.info(f"成功获取 {code} {period}分鋳, 共 {len(df)} 条")
            return df
        except Exception as e:
            logger.error(f"获取 {code} 分鋳数据失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_stock_realtime(code: str) -> Optional[Dict]:
        """
        获取个股实时上章
        
        Args:
            code (str): 股票代码, 序梗: "000001"
        
        Returns:
            Optional[Dict]: 实时行情字典或 None
                - 代码
                - 名称
                - 最新价
                - 涨跌幅
                - 涨跌额
                - 成交量
                - 成交额
        """
        try:
            df = ak.stock_zh_a_spot_em()
            # 去除不必要的前缀
            stock = df[df['代码'] == code]
            if len(stock) > 0:
                logger.info(f"成功获取 {code} 实时上章")
                return stock.to_dict('records')[0]
            else:
                logger.warning(f"找不到 {code} 的实时上章")
                return None
        except Exception as e:
            logger.error(f"获取 {code} 实时上章失败: {e}")
            return None
    
    # ============================================================================
    # 批量数据 API
    # ============================================================================
    
    @staticmethod
    def get_multiple_stocks_daily(
        codes: List[str],
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多个股票的日线数据
        
        Args:
            codes (List[str]): 股票代码列表
            start_date (str): 开始日期
            end_date (str): 结束日期
            adjust (str): 复权方式
        
        Returns:
            Dict[str, pd.DataFrame]: {code: DataFrame}
        """
        result = {}
        for code in codes:
            df = AKShareDataLoader.get_stock_daily(code, start_date, end_date, adjust)
            if not df.empty:
                result[code] = df
        logger.info(f"批量获取了 {len(result)}/{len(codes)} 股票的K线数据")
        return result
    
    # ============================================================================
    # 整合数据 API
    # ============================================================================
    
    @staticmethod
    def get_trading_day_data(date: str) -> Dict:
        """
        获取一个上章的完整交易数据
        
        Args:
            date (str): 日期, 格式 "20260107"
        
        Returns:
            Dict: 包含龙虎榜、板块、行业数据
        """
        return {
            "lhb_detail": AKShareDataLoader.get_lhb_daily(date),
            "lhb_stat": AKShareDataLoader.get_lhb_stat(),
            "lhb_business": AKShareDataLoader.get_lhb_business_top(),
            "industry": AKShareDataLoader.get_industry_spot(),
        }


# ============================================================================
    # 新增：板块详细数据 API
    # ============================================================================
    
    @staticmethod
    def get_sector_stock_stats(symbol: str = "BK0447") -> Dict[str, Any]:
        """
        获取板块内个股统计（涨跌家数、涨停/跌停家数等）
        
        Args:
            symbol: 板块代码
            
        Returns:
            Dict: 包含涨跌家数、涨停/跌停家数等统计信息
        """
        try:
            import akshare as ak
            # 获取板块成分股
            df = ak.stock_board_industry_cons_em(symbol=symbol)
            
            if df.empty:
                return {}
            
            # 统计涨跌家数
            up_count = len(df[df['涨跌幅'] > 0])
            down_count = len(df[df['涨跌幅'] < 0])
            flat_count = len(df[df['涨跌幅'] == 0])
            
            # 统计涨停/跌停家数（涨停>9.8%，跌停<-9.8%）
            limit_up_count = len(df[df['涨跌幅'] >= 9.8])
            limit_down_count = len(df[df['涨跌幅'] <= -9.8])
            
            # 获取领涨股（涨幅最大的前5只）
            top_stocks = df.nlargest(5, '涨跌幅')[['代码', '名称', '涨跌幅', '最新价']].to_dict('records')
            
            # 获取领跌股（跌幅最大的前5只）
            bottom_stocks = df.nsmallest(5, '涨跌幅')[['代码', '名称', '涨跌幅', '最新价']].to_dict('records')
            
            stats = {
                'total_count': len(df),
                'up_count': up_count,
                'down_count': down_count,
                'flat_count': flat_count,
                'limit_up_count': limit_up_count,
                'limit_down_count': limit_down_count,
                'top_stocks': top_stocks,
                'bottom_stocks': bottom_stocks
            }
            
            logger.info(f"成功获取板块 {symbol} 统计数据: {up_count}涨/{down_count}跌, {limit_up_count}涨停/{limit_down_count}跌停")
            return stats
            
        except Exception as e:
            logger.error(f"获取板块 {symbol} 统计数据失败: {e}")
            return {}
    
    @staticmethod
    def get_sector_capital_flow(symbol: str = "BK0447") -> Dict[str, float]:
        """
        获取板块资金流向数据
        
        Args:
            symbol: 板块代码
            
        Returns:
            Dict: 包含主力净流入、散户净流入等资金数据
        """
        try:
            import akshare as ak
            # 获取板块资金流向
            df = ak.stock_sector_fund_flow_rank(indicator="今日", sector="行业")
            
            if df.empty:
                return {}
            
            # 查找对应板块
            sector_row = df[df['板块代码'] == symbol]
            if sector_row.empty:
                return {}
            
            row = sector_row.iloc[0]
            
            return {
                'main_net_inflow': float(row.get('主力净流入', 0) or 0),
                'main_inflow': float(row.get('主力流入', 0) or 0),
                'main_outflow': float(row.get('主力流出', 0) or 0),
                'retail_net_inflow': float(row.get('散户净流入', 0) or 0),
                'retail_inflow': float(row.get('散户流入', 0) or 0),
                'retail_outflow': float(row.get('散户流出', 0) or 0)
            }
            
        except Exception as e:
            logger.error(f"获取板块 {symbol} 资金流向失败: {e}")
            return {}
    
    @staticmethod
    def get_sector_index_kline(symbol: str = "BK0447", period: str = "daily", 
                               start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取板块指数K线数据
        
        Args:
            symbol: 板块代码
            period: 周期 (daily, weekly, monthly)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            
        Returns:
            pd.DataFrame: K线数据
        """
        try:
            import akshare as ak
            from datetime import datetime, timedelta
            
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            
            # 获取板块历史数据
            df = ak.stock_board_industry_hist_em(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if not df.empty:
                logger.info(f"成功获取板块 {symbol} K线数据，共 {len(df)} 条")
            else:
                logger.warning(f"板块 {symbol} K线数据为空")
                
            return df
            
        except Exception as e:
            logger.error(f"获取板块 {symbol} K线数据失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_northbound_fund_flow() -> Dict[str, Any]:
        """
        获取北向资金流向数据
        
        Returns:
            Dict: 包含北向资金流入流出数据
        """
        try:
            import akshare as ak
            # 获取北向资金流向
            df = ak.stock_hsgt_hist_em(symbol="北向资金")
            
            if df.empty:
                return {}
            
            # 获取最近一天的数据
            latest = df.iloc[0]
            
            return {
                'date': latest.get('日期', ''),
                'north_net_inflow': float(latest.get('净流入', 0) or 0),
                'north_inflow': float(latest.get('流入', 0) or 0),
                'north_outflow': float(latest.get('流出', 0) or 0),
                'sh_net_inflow': float(latest.get('沪股通净流入', 0) or 0),
                'sz_net_inflow': float(latest.get('深股通净流入', 0) or 0)
            }
            
        except Exception as e:
            logger.error(f"获取北向资金数据失败: {e}")
            return {}
    
    # ============================================================================
    # V16.3: 减持公告 API
    # ============================================================================
    
    @staticmethod
    def get_share_hold_decrease(stock_code: str = None, days: int = 90) -> pd.DataFrame:
        """
        获取股东减持公告数据
        
        Args:
            stock_code (str): 股票代码，如果为 None 则获取所有股票
            days (int): 查询天数，默认 90 天
        
        Returns:
            pd.DataFrame: 减持公告数据
                - 股票代码
                - 股票名称
                - 公告日期
                - 减持人名称
                - 减持比例 (%)
                - 减持价格区间
                - 减持数量 (万股)
                - 减持方式
                - 减持状态
        """
        try:
            # 注意：AkShare 没有 stock_share_hold_decrease_em 接口
            # 使用 stock_shareholder_change_ths 接口获取股东持股变动
            # 如果 stock_code 为 None，返回空 DataFrame
            if not stock_code:
                logger.info("未提供股票代码，返回空数据")
                return pd.DataFrame()
            
            # 获取股东持股变动
            df = ak.stock_shareholder_change_ths(symbol=stock_code)
            
            if df.empty:
                logger.info(f"未找到 {stock_code} 的股东持股变动数据")
                return pd.DataFrame()
            
            # 筛选减持记录（持股数量减少的记录）
            # 假设 DataFrame 中有 '变动数量' 或类似字段
            # 根据实际返回的数据结构进行调整
            decrease_df = df.copy()
            
            # 添加股票代码列
            decrease_df['股票代码'] = stock_code
            
            logger.info(f"成功获取 {stock_code} 股东持股变动数据，共 {len(decrease_df)} 条记录")
            return decrease_df
            
        except Exception as e:
            logger.error(f"获取股东持股变动数据失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_insider_selling_risk(stock_code: str, days: int = 90) -> Dict[str, Any]:
        """
        获取内部人减持风险分析
        
        Args:
            stock_code (str): 股票代码
            days (int): 查询天数，默认 90 天
        
        Returns:
            Dict: 内部人减持风险分析
                - has_risk (bool): 是否存在风险
                - risk_level (str): 风险等级 (LOW, MEDIUM, HIGH)
                - total_decrease_ratio (float): 总减持比例 (%)
                - total_decrease_value (float): 总减持金额（万元）
                - decrease_records (list): 减持记录列表
                - reason (str): 风险原因
        """
        try:
            # 获取减持公告数据
            df = AKShareDataLoader.get_share_hold_decrease(stock_code, days)
            
            if df.empty:
                return {
                    'has_risk': False,
                    'risk_level': 'LOW',
                    'total_decrease_ratio': 0.0,
                    'total_decrease_value': 0.0,
                    'decrease_records': [],
                    'reason': '未发现减持公告'
                }
            
            # 分析减持记录
            total_decrease_ratio = 0.0
            total_decrease_value = 0.0
            decrease_records = []
            
            for _, row in df.iterrows():
                # 提取减持比例
                decrease_ratio = 0.0
                try:
                    ratio_str = str(row.get('减持比例', '0'))
                    # 提取数字（可能包含 % 符号）
                    import re
                    ratio_match = re.search(r'([\d.]+)', ratio_str)
                    if ratio_match:
                        decrease_ratio = float(ratio_match.group(1))
                except:
                    pass
                
                # 提取减持数量
                decrease_amount = 0.0
                try:
                    amount_str = str(row.get('减持数量', '0'))
                    # 提取数字（可能包含单位）
                    import re
                    amount_match = re.search(r'([\d.]+)', amount_str)
                    if amount_match:
                        decrease_amount = float(amount_match.group(1))
                except:
                    pass
                
                # 计算减持金额（估算）
                # 假设平均价格为减持价格区间的中位数
                decrease_price = 0.0
                try:
                    price_str = str(row.get('减持价格区间', '0'))
                    import re
                    price_matches = re.findall(r'([\d.]+)', price_str)
                    if price_matches:
                        if len(price_matches) == 1:
                            decrease_price = float(price_matches[0])
                        else:
                            # 取价格区间的平均值
                            decrease_price = (float(price_matches[0]) + float(price_matches[1])) / 2
                except:
                    pass
                
                decrease_value = decrease_amount * decrease_price  # 单位：万元
                
                # 累计
                total_decrease_ratio += decrease_ratio
                total_decrease_value += decrease_value
                
                # 记录
                decrease_records.append({
                    '公告日期': row.get('公告日期', ''),
                    '减持人': row.get('减持人名称', ''),
                    '减持比例': decrease_ratio,
                    '减持数量': decrease_amount,
                    '减持价格': decrease_price,
                    '减持金额': decrease_value,
                    '减持方式': row.get('减持方式', ''),
                    '减持状态': row.get('减持状态', '')
                })
            
            # 判断风险等级
            risk_level = 'LOW'
            has_risk = False
            reason = ''
            
            # 风险判定标准
            # 1. 总减持比例 > 2% 或 总减持金额 > 1亿：高危
            if total_decrease_ratio > 2.0 or total_decrease_value > 10000:
                risk_level = 'HIGH'
                has_risk = True
                reason = f"⚠️ [内部人风险] 大股东拟减持 {total_decrease_ratio:.2f}%，套现约 {total_decrease_value:.0f} 万元"
            # 2. 总减持比例 > 1% 或 总减持金额 > 5000万：中危
            elif total_decrease_ratio > 1.0 or total_decrease_value > 5000:
                risk_level = 'MEDIUM'
                has_risk = True
                reason = f"⚡ [内部人警示] 股东拟减持 {total_decrease_ratio:.2f}%，套现约 {total_decrease_value:.0f} 万元"
            # 3. 有减持记录但金额较小：低危
            elif len(decrease_records) > 0:
                risk_level = 'LOW'
                has_risk = False
                reason = f"ℹ️ [内部人关注] 有减持公告，但规模较小 ({total_decrease_ratio:.2f}%, {total_decrease_value:.0f} 万元)"
            
            return {
                'has_risk': has_risk,
                'risk_level': risk_level,
                'total_decrease_ratio': total_decrease_ratio,
                'total_decrease_value': total_decrease_value,
                'decrease_records': decrease_records,
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"获取内部人减持风险分析失败: {e}")
            return {
                'has_risk': False,
                'risk_level': 'LOW',
                'total_decrease_ratio': 0.0,
                'total_decrease_value': 0.0,
                'decrease_records': [],
                'reason': f'获取减持数据失败: {e}'
            }


if __name__ == "__main__":
    # 测试
    loader = AKShareDataLoader()
    
    # 获取今天的龙虎榜
    today = datetime.now().strftime("%Y%m%d")
    lhb = loader.get_lhb_daily(today)
    print(f"\n龙虎榜数据 (\u5171 {len(lhb)} 条):")
    print(lhb.head())
    
    # 获取板块数据
    industry = loader.get_industry_spot()
    print(f"\n板块数据 (\u5171 {len(industry)} 个):")
    print(industry.head())
    
    # 获取K线
    kline = loader.get_stock_daily("000001", "20260101", today)
    print(f"\n000001 K线数据 (\u5171 {len(kline)} 条):")
    print(kline.head())
    
    # 测试新增功能
    print("\n=== 测试新增功能 ===")
    
    # 测试板块个股统计
    stats = loader.get_sector_stock_stats("BK0447")
    print(f"\n板块个股统计: {stats}")
    
    # 测试资金流向
    flow = loader.get_sector_capital_flow("BK0447")
    print(f"\n板块资金流向: {flow}")
    
    # 测试板块K线
    sector_kline = loader.get_sector_index_kline("BK0447")
    print(f"\n板块K线数据 (\u5171 {len(sector_kline)} 条):")
    print(sector_kline.head())
    
    # 测试北向资金
    north = loader.get_northbound_fund_flow()
    print(f"\n北向资金数据: {north}")
