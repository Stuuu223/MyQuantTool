import akshare as ak
import pandas as pd
import concurrent.futures
from datetime import datetime
import config.config_system as config

class TechnicalAnalyzer:
    def __init__(self):
        # 获取去年年份，作为数据起点，减少数据量提升速度
        self.start_date = (datetime.now().year - 1).__str__() + "0101"

    def _fetch_single_stock(self, code, real_time_price=None):
        """
        内部方法：获取单只股票数据并分析趋势
        
        Args:
            code: 股票代码
            real_time_price: 实时价格（可选，用于盘中实时分析）
        
        Returns:
            str: 技术分析结果字符串
        """
        try:
            # 1. 清洗代码格式 (兼容 sh600519 -> 600519)
            clean_code = code.replace("sh", "").replace("sz", "")
            
            # 2. 获取日线数据 (前复权)
            # 注意：akshare 接口可能会偶尔超时，这里是耗时点
            df = ak.stock_zh_a_hist(symbol=clean_code, period="daily", start_date=self.start_date, adjust="qfq")
            
            if df.empty or len(df) < config.THRESHOLD_MA_PERIOD:
                return "⚪ 数据不足"

            # 3. 只需要最近 60 天的数据
            df = df.tail(config.THRESHOLD_HISTORY_DAYS).reset_index(drop=True)
            
            # 4. 计算核心均线
            df['MA5'] = df['收盘'].rolling(window=5).mean()
            df['MA10'] = df['收盘'].rolling(window=10).mean()
            df['MA20'] = df['收盘'].rolling(window=config.THRESHOLD_MA_PERIOD) # 辅助
            
            # 🔥 V10.1.9.1 修复：实时价格注入 (Real-Time Injection)
            # 如果传入了实时价格，就用实时的；否则用历史收盘价（降级方案）
            if real_time_price is not None and real_time_price > 0:
                current_price = float(real_time_price)
            else:
                current_price = df.iloc[-1]['收盘']  # 降级方案：使用历史收盘价
            
            # 获取均线值 (均线还是用历史数据算的，这没问题)
            ma5 = df.iloc[-1]['MA5']
            ma10 = df.iloc[-1]['MA10']
            ma20 = df.iloc[-1]['MA20']
            
            # --- 趋势判定逻辑 ---
            tags = []
            score = 0
            
            # A. 均线排列判断
            if ma5 > ma10 > ma20:
                tags.append("📈 多头排列")
                score += 2
            elif ma5 < ma10 < ma20:
                tags.append("📉 空头排列")
                score -= 2
            
            # B. 生命线判定 (20日线)
            if current_price > ma20:
                tags.append("🟢 站上20日线")
                score += 1
            else:
                tags.append("🔴 跌破20日线")
                score -= 2
                
            # C. 乖离率 (Bias) - 防止追高
            # (现价 - 5日线) / 5日线
            bias_5 = (current_price - ma5) / ma5 * 100
            if bias_5 > config.THRESHOLD_BIAS_HIGH:
                tags.append("⚠️ 短期超买")
                score -= 1
            elif bias_5 < config.THRESHOLD_BIAS_LOW:
                tags.append("💎 短期超跌")
                score += 1
                
            # 生成结论
            if not tags:
                result_str = "🔁 震荡趋势"
            else:
                result_str = " ".join(tags)
            
            return f"{result_str}"

        except Exception as e:
            return f"⚪ 分析失败"

    def analyze_batch(self, stock_list):
        """
        🚀 并发分析多只股票 (多线程加速)
        
        Args:
            stock_list: 包含 'code' 和 'price'/'最新价' 字段的字典列表
        
        Returns:
            dict: 字典 { '600xxx': '📈 多头排列...', ... }
        
        Note:
            - V10.1.9.1 修复：支持实时价格注入，避免"昨日幻影"问题
            - 优先使用 stock['price'] 或 stock['最新价'] 作为实时价格
            - 如果没有实时价格，自动降级使用历史收盘价
        """
        results = {}
        # ⚠️ 战术优化：只取前 8 名进行深度分析，避免请求过多被封IP或卡顿
        target_stocks = stock_list[:8] 
        
        # 使用线程池并发请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # 🔥 V10.1.9.1 修复：将实时价格传入任务
            # 兼容多种价格字段：'price', '最新价', 'current_price'
            future_to_code = {}
            for stock in target_stocks:
                # 尝试获取实时价格（支持多种字段名）
                real_time_price = stock.get('price') or stock.get('最新价') or stock.get('current_price')
                
                # 提交任务，传入实时价格
                future = executor.submit(
                    self._fetch_single_stock, 
                    stock['code'], 
                    real_time_price=real_time_price
                )
                future_to_code[future] = stock['code']
            
            # 获取结果
            for future in concurrent.futures.as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    data = future.result()
                    results[code] = data
                except Exception:
                    results[code] = "⚪ 分析异常"
                    
        return results