"""
🛡️ DataSanitizer - 数据消毒器
V8.4: 数据防火墙，在数据进入系统的那一刻进行"核酸检测"

核心思路：利用"金融常识"反向排错
- 常识A：集合竞价的换手率不可能超过20%（除非是刚上市第一天的新股）
- 常识B：A股单笔竞价成交额很难超过50亿（哪怕是茅台）
"""

class DataSanitizer:
    """数据消毒器：统一清洗和规范化所有数据源的数据"""
    
    @staticmethod
    def normalize_volume(volume, price, circulating_cap_shares=None, source_type='unknown'):
        """
        全能成交量清洗器
        目标：统统转换为【手】(Lots)
        
        Args:
            volume: 原始成交量（可能是股或手）
            price: 当前价格
            circulating_cap_shares: 流通股本（股数）
            source_type: 数据源类型 ('easyquotation', 'akshare', 'tencent', 'unknown')
        
        Returns:
            int: 清洗后的成交量（手数）
        """
        if volume is None or volume == 0:
            return 0
        
        clean_vol = float(volume)
        
        # --- 规则 1: 针对已知数据源的硬编码修正 ---
        # Easyquotation (新浪源) 返回的 volume 永远是股
        if source_type in ['easyquotation', 'sina']:
            clean_vol = clean_vol / 100
            return int(clean_vol)
        
        # --- 规则 2: 暴力修正 - 基于成交量大小判断 ---
        # 如果成交量 > 500万手，那几乎肯定是个BUG（单位是股）
        # 17437873 手 = 1700万手 = 17亿股 -> 极其罕见
        if clean_vol > 5_000_000:  # 500万手阈值
            clean_vol = clean_vol / 100
        
        # --- 规则 3: 利用流通盘验证 (最稳) ---
        if circulating_cap_shares and circulating_cap_shares > 0:
            # 计算换手率（假设 volume 是手，circulating 是股）
            turnover_if_lots = (clean_vol * 100) / circulating_cap_shares
            
            # 如果竞价换手率 > 50% (这是不可能的，除非新股首日)
            if turnover_if_lots > 0.5:
                clean_vol = clean_vol / 100
        
        # --- 规则 4: 基于金额的熔断检查 ---
        # 估算成交金额 = 手数 * 100 * 价格
        estimated_amount = clean_vol * 100 * price
        
        # 如果竞价阶段金额 > 20亿 (很少有股票竞价能成交20亿，除了超级大盘股)
        if estimated_amount > 2_000_000_000:  # 20亿
            # 尝试修正：可能是单位错误
            clean_vol = clean_vol / 100
        
        return int(clean_vol)
    
    @staticmethod
    def normalize_auction_aggression(current_vol, avg_vol):
        """
        清洗竞价抢筹度 (修复 690671.74% 这种离谱数据)
        
        Args:
            current_vol: 当前成交量（手数）
            avg_vol: 平均成交量（手数）
        
        Returns:
            float: 清洗后的竞价抢筹度（百分比）
        """
        if avg_vol is None or avg_vol == 0:
            return 0.0
        
        # 1. 确保量纲一致
        ratio = (current_vol / avg_vol) * 100
        
        # 2. 异常值熔断 (Sanity Check)
        # 抢筹度超过 5000% (50倍) 极其罕见，通常是分母 avg_vol 出错或数据源没对齐
        if ratio > 5000:
            # 数据不可信，直接归零，不参与评分，避免误导
            return 0.0
        
        return round(ratio, 2)
    
    @staticmethod
    def normalize_seal_amount(bid1_volume, price, source_type='unknown'):
        """
        清洗封单金额
        
        Args:
            bid1_volume: 买一量（手数或股数）
            price: 当前价格
            source_type: 数据源类型
        
        Returns:
            float: 封单金额（万元）
        """
        if bid1_volume is None or bid1_volume == 0 or price is None or price == 0:
            return 0.0
        
        # Easyquotation 的 bid1_volume 已经是手数
        if source_type in ['easyquotation', 'sina']:
            # 封单金额 = 买一量（手数）× 100（股/手）× 价格 / 10000（转换为万）
            seal_amount = bid1_volume * 100 * price / 10000
        else:
            # 假设是股数，需要先转换为手数
            seal_amount = (bid1_volume / 100) * 100 * price / 10000
        
        # 异常值检查：封单金额 > 100亿（1000000万）几乎不可能
        if seal_amount > 1_000_000:
            # 尝试修正：可能是单位错误
            seal_amount = seal_amount / 100
        
        return round(seal_amount, 2)
    
    @staticmethod
    def validate_auction_data(symbol, auction_volume, auction_amount, price, circulating_shares=None):
        """
        综合验证竞价数据的合理性
        
        Args:
            symbol: 股票代码
            auction_volume: 竞价成交量（手数）
            auction_amount: 竞价成交额（万元）
            price: 当前价格
            circulating_shares: 流通股本（股数）
        
        Returns:
            tuple: (is_valid, reason)
        """
        # 检查1：竞价换手率
        if circulating_shares and circulating_shares > 0:
            auction_turnover = (auction_volume * 100) / circulating_shares
            if auction_turnover > 0.2:  # 竞价换手率 > 20%
                return False, f"竞价换手率异常: {auction_turnover*100:.2f}% > 20%"
        
        # 检查2：竞价成交额
        if auction_amount > 500_000:  # > 500亿
            return False, f"竞价成交额异常: {auction_amount:.2f}万 > 500亿"
        
        # 检查3：价格合理性
        if price < 0.1 or price > 1000:
            return False, f"价格异常: {price}"
        
        return True, "数据正常"
    
    @staticmethod
    def calculate_amount_from_volume(volume_lots, price):
        """
        统一金额计算器：永远记得乘以 100
        
        Args:
            volume_lots: 成交量（手数）
            price: 价格（元）
        
        Returns:
            float: 金额（元）
        """
        if volume_lots is None or price is None:
            return 0.0
        
        # 核心修复：手 -> 股
        return volume_lots * 100 * price
    
    @staticmethod
    def format_amount_to_display(amount):
        """
        自动格式化显示 (万/亿)
        
        Args:
            amount: 金额（元）
        
        Returns:
            str: 格式化后的金额字符串
        """
        if amount > 100000000:
            return f"{amount/100000000:.2f} 亿"
        else:
            return f"{amount/10000:.2f} 万"
    
    @staticmethod
    def sanitize_realtime_data(raw_data, source_type='easyquotation', stock_info=None, code=None):
        """
        一站式实时数据清洗
        
        Args:
            raw_data: 原始实时数据（字典）
            source_type: 数据源类型
            stock_info: 股票基本信息（含流通股本等）
            code: 股票代码（可选，用于 easyquotation 数据源）
        
        Returns:
            dict: 清洗后的数据
        """
        if not raw_data:
            return {}
        
        sanitized = raw_data.copy()
        
        # 🆕 添加股票代码（easyquotation 数据源需要）
        if code:
            sanitized['code'] = code
        
        # 获取基本信息
        price = float(raw_data.get('now', raw_data.get('price', 0)))
        circulating_shares = stock_info.get('circulating_shares') if stock_info else None
        
        # 1. 清洗成交量
        raw_volume = float(raw_data.get('volume', 0))
        clean_volume = DataSanitizer.normalize_volume(
            raw_volume, price, circulating_shares, source_type
        )
        sanitized['volume'] = clean_volume
        
        # 2. 清洗买一量/卖一量
        if 'bid1_volume' in raw_data:
            sanitized['bid1_volume'] = DataSanitizer.normalize_volume(
                float(raw_data['bid1_volume']), price, circulating_shares, source_type
            )
        if 'ask1_volume' in raw_data:
            sanitized['ask1_volume'] = DataSanitizer.normalize_volume(
                float(raw_data['ask1_volume']), price, circulating_shares, source_type
            )
        
        # 3. 重新计算成交额（不要信 API 返回的 amount，自己算最准）
        # 金额 = 手数 * 100 * 价格 / 10000（转换为万）
        sanitized['amount'] = clean_volume * 100 * price / 10000
        
        # 4. 清洗封单金额
        if 'bid1_volume' in sanitized:
            sanitized['seal_amount'] = DataSanitizer.normalize_seal_amount(
                sanitized['bid1_volume'], price, source_type
            )
        
        return sanitized