from openai import OpenAI
import os

class DeepSeekAgent:
    # 类名保持不变以兼容主程序
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = None
        if api_key and not api_key.startswith("sk-"):
            try:
                # 使用硅基流动 API（提供 2000 万免费 tokens）
                # 访问 https://siliconflow.cn/ 注册获取 API Key
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.siliconflow.cn/v1"
                )
            except Exception as e:
                print(f"DeepSeek 配置失败: {e}")

    def analyze_stock(self, symbol, price_change, technical_data):
        """
        AI 智能分析股票
        
        Args:
            symbol: 股票代码
            price_change: 涨跌幅
            technical_data: 技术指标字典，包含：
                - current_price: 当前价格
                - resistance_levels: 阻力位列表
                - support_levels: 支撑位列表
                - atr: ATR 波动率
                - macd: MACD 指标
                - rsi: RSI 指标
                - bollinger: 布林带数据
        """
        if not self.api_key or self.api_key.startswith("sk-"):
            return "⚠️ 请先配置 DeepSeek API Key (需在 main.py 中填入)"

        if not self.client:
            return "⚠️ 模型未初始化，请检查网络或 Key"

        # 构建专业的量化分析提示词
        prompt = f'''
你是一位拥有20年A股实战经验的资深量化分析师，擅长结合技术指标和筹码分布进行投资决策。现在请为一位股市小白投资者分析以下股票：

【基本信息】
股票代码：{symbol}
当前价格：{technical_data.get('current_price', 0)}
今日涨跌幅：{price_change}%

【技术指标分析】
1. 阻力位：{technical_data.get('resistance_levels', [])}
2. 支撑位：{technical_data.get('support_levels', [])}
3. 波动率（ATR）：{technical_data.get('atr', 0)}
4. MACD：{technical_data.get('macd', {})}
5. RSI：{technical_data.get('rsi', {})}
6. 布林带：{technical_data.get('bollinger', {})}

【分析要求】
请以通俗易懂的语言（适合股市小白理解），从以下三个维度进行分析：

1. **当前状态判断**：结合各项技术指标，判断当前股价处于什么状态（强势上涨、弱势下跌、震荡整理等）

2. **风险提示**：根据指标信号，提示当前的主要风险点（如：RSI超买可能回调、接近阻力位等）

3. **操作建议**：给出明确的操作建议（买入/卖出/持有），并说明理由和参考价位

【格式要求】
- 总字数控制在 200-300 字
- 使用简单易懂的语言，避免过多专业术语
- 给出具体的价格参考点位
- 语气客观理性，不做夸大宣传
'''
        
        try:
            response = self.client.chat.completions.create(
                model='deepseek-ai/DeepSeek-V3',
                messages=[
                    {
                        'role': 'system', 
                        'content': '你是一位专业的A股量化分析师，擅长技术分析和投资策略制定。你的分析要客观、理性、专业，同时要让普通投资者能够理解。'
                    },
                    {'role': 'user', 'content': prompt}
                ],
                temperature=0.3,  # 降低温度，使分析更稳定
                max_tokens=400
            )
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                return "⚠️ 触发免费版速率限制，请稍等几秒再试。"
            elif "401" in error_str or "403" in error_str:
                return "⚠️ API Key 无效或无权限，请检查您的 Key。"
            return f"AI 分析失败: {e}"
