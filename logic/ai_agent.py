"""
AI 智能代理（Lite 版）
使用 LLM API 替代硬编码规则，实现真正的智能分析

V15 "The AI Demotion" 更新：
- 将 AI 从"决策者"降级为"信息提取器（ETL）"
- AI 不再进行价值判断，只做数据清洗和结构化提取
- 相信钱（DDE），相信势（Trend），别相信嘴（AI）
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging
import json
from logic.predictive_engine import PredictiveEngine

logger = logging.getLogger(__name__)


class RealAIAgent:
    """
    真正的 AI 智能代理
    基于 LLM API 的股票分析系统
    """

    def __init__(self, api_key: str, provider: str = 'openai', model: str = 'gpt-4', use_dragon_tactics: bool = False):
        """
        初始化 AI 代理

        Args:
            api_key: API 密钥
            provider: 提供商 ('openai', 'anthropic', 'deepseek', 'zhipu' 等)
            model: 模型名称
            use_dragon_tactics: 是否使用龙头战法（V3.0 暴力版）
        """
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.use_dragon_tactics = use_dragon_tactics
        self.llm = self._init_llm()
        
        # 🆕 V12 接入预测引擎
        self.pe = PredictiveEngine()
        
        # 初始化龙头战法
        if use_dragon_tactics:
            try:
                from logic.dragon_tactics import DragonTactics
                self.dragon_tactics = DragonTactics()
            except ImportError:
                logger.warning("无法导入 DragonTactics，龙头战法功能不可用")
                self.dragon_tactics = None
        else:
            self.dragon_tactics = None

    def _init_llm(self):
        """初始化 LLM 接口"""
        try:
            from logic.llm_interface import DeepSeekProvider, OpenAIProvider

            # 根据提供商选择对应的类
            if self.provider == 'deepseek':
                return DeepSeekProvider(api_key=self.api_key)
            elif self.provider == 'openai':
                return OpenAIProvider(api_key=self.api_key)
            else:
                # 默认使用 DeepSeek
                return DeepSeekProvider(api_key=self.api_key)
        except ImportError:
            logger.error("无法导入 LLM 接口，请检查 llm_interface.py")
            return None
    
    # 🆕 V15 "The AI Demotion" - AI 降级为信息提取器（ETL）
    def extract_structured_info(self, text: str) -> Dict[str, Any]:
        """
        V15 新功能：从新闻文本中提取结构化信息
        
        AI 的角色：从"决策者"降级为"信息提取器（ETL）"
        AI 不再进行价值判断，只做数据清洗和结构化提取
        
        Args:
            text: 新闻文本内容
        
        Returns:
            结构化信息字典
            {
                'is_official_announcement': bool,  # 是否为上市公司官方公告
                'contract_amount': float/null,      # 合同金额（亿元）
                'risk_warning': bool,               # 是否包含风险词
                'core_concepts': list,              # 核心概念列表
                'risk_keywords': list,              # 发现的风险关键词
                'parties': list                     # 涉及的甲方/乙方
            }
        """
        # 处理 None 或空输入
        if text is None or not isinstance(text, str):
            return {
                'is_official_announcement': False,
                'contract_amount': None,
                'risk_warning': False,
                'core_concepts': [],
                'risk_keywords': [],
                'parties': []
            }
        
        if self.llm is None:
            # 如果没有 LLM，使用规则提取
            return self._rule_based_extract(text)
        
        # 构建结构化提取的 Prompt
        prompt = f"""【任务】
从以下新闻文本中提取结构化数据。这是一个纯粹的信息提取任务，不需要你发表任何观点或预测。

【文本】
{text}

【输出格式】
请务必只返回标准的 JSON 格式，不要包含 markdown 标记或其他文字：
{{
    "is_official_announcement": true/false,
    "contract_amount": 合同金额（亿元，如果没有则为null）,
    "risk_warning": true/false,
    "core_concepts": ["概念1", "概念2", ...],
    "risk_keywords": ["风险词1", "风险词2", ...],
    "parties": ["甲方名称", "乙方名称", ...]
}}

【提取规则】
1. is_official_announcement: 如果文本包含"公告"、"公告编号"、"董事会"、"股东大会"等官方公告特征，则为 true
2. contract_amount: 提取合同金额，单位转换为亿元。如果没有明确金额，则为 null
3. risk_warning: 如果包含"监管函"、"立案"、"警示"、"处罚"、"退市风险"、"ST"、"*ST"等风险词，则为 true
4. core_concepts: 提取文本中提及的核心概念（如"低空经济"、"固态电池"、"人形机器人"、"AI芯片"等）
5. risk_keywords: 列出所有发现的风险关键词
6. parties: 提取涉及的甲方、乙方、合作方名称

【重要】
- 严禁输出任何关于股价涨跌的主观预测
- 严禁输出"看好"、"推荐"、"买入"、"卖出"等投资建议
- 只做事实提取，不做价值判断
- 如果不确定某个字段，填 null 或空列表

请只返回 JSON，不要有任何其他文字。"""
        
        try:
            # 调用 LLM
            response = self.llm.chat(prompt, model=self.model)
            
            # 提取响应内容
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            # 解析 JSON
            import re
            cleaned = re.sub(r'```json\s*|\s*```', '', response_text).strip()
            result = json.loads(cleaned)
            
            # 验证和补充默认值
            if 'is_official_announcement' not in result:
                result['is_official_announcement'] = False
            if 'contract_amount' not in result:
                result['contract_amount'] = None
            if 'risk_warning' not in result:
                result['risk_warning'] = False
            if 'core_concepts' not in result:
                result['core_concepts'] = []
            if 'risk_keywords' not in result:
                result['risk_keywords'] = []
            if 'parties' not in result:
                result['parties'] = []
            
            logger.info(f"V15 ETL 提取成功: 发现 {len(result['core_concepts'])} 个概念, 风险={result['risk_warning']}")
            
            return result
            
        except Exception as e:
            logger.error(f"V15 ETL 提取失败: {e}")
            # 降级到规则提取
            return self._rule_based_extract(text)
    
    def _rule_based_extract(self, text: str) -> Dict[str, Any]:
        """
        规则提取（当 LLM 不可用时使用）
        
        Args:
            text: 新闻文本内容
        
        Returns:
            结构化信息字典
        """
        import re
        
        result = {
            'is_official_announcement': False,
            'contract_amount': None,
            'risk_warning': False,
            'core_concepts': [],
            'risk_keywords': [],
            'parties': []
        }
        
        # 1. 判断是否为官方公告
        official_keywords = ['公告', '公告编号', '董事会', '股东大会', '监事会', '独立董事']
        if any(keyword in text for keyword in official_keywords):
            result['is_official_announcement'] = True
        
        # 2. 提取合同金额
        amount_patterns = [
            r'(\d+(?:\.\d+)?)\s*亿元',
            r'(\d+(?:\.\d+)?)\s*万',
            r'合同金额[：:]\s*(\d+(?:\.\d+)?)',
            r'中标金额[：:]\s*(\d+(?:\.\d+)?)'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text)
            if match:
                amount = float(match.group(1))
                if '万' in match.group(0):
                    amount = amount / 10000  # 转换为亿元
                result['contract_amount'] = amount
                break
        
        # 3. 风险关键词检测
        risk_keywords_list = [
            '监管函', '立案', '警示', '处罚', '退市风险', 'ST', '*ST',
            '违规', '造假', '内幕交易', '操纵市场', '虚假陈述'
        ]
        
        found_risk_keywords = []
        for keyword in risk_keywords_list:
            if keyword in text:
                found_risk_keywords.append(keyword)
        
        if found_risk_keywords:
            result['risk_warning'] = True
            result['risk_keywords'] = found_risk_keywords
        
        # 4. 核心概念提取（简化版）
        # 这里可以扩展更多的概念关键词
        concept_keywords = [
            '低空经济', '固态电池', '人形机器人', 'AI芯片', 'CPO', '算力',
            '华为', '小米', '苹果', '英伟达', '特斯拉',
            '新能源', '光伏', '风电', '储能', '氢能',
            '半导体', '集成电路', '芯片',
            '生物医药', '疫苗', '创新药',
            '数字经济', '云计算', '大数据', '区块链',
            '元宇宙', '虚拟现实', '增强现实'
        ]
        
        found_concepts = []
        for concept in concept_keywords:
            if concept in text:
                found_concepts.append(concept)
        
        result['core_concepts'] = found_concepts
        
        logger.info(f"V15 规则提取: 发现 {len(found_concepts)} 个概念, 风险={result['risk_warning']}")
        
        return result

    def analyze_stock(self,
                     symbol: str,
                     price_data: Dict[str, Any],
                     technical_data: Dict[str, Any],
                     market_context: Optional[Dict[str, Any]] = None,
                     return_json: bool = True,
                     use_dragon_tactics: Optional[bool] = None) -> Dict[str, Any]:
        """
        使用 LLM 分析股票

        Args:
            symbol: 股票代码
            price_data: 价格数据（当前价格、涨跌幅等）
            technical_data: 技术指标数据
            market_context: 市场上下文（可选）
            return_json: 是否返回 JSON 格式（默认 True）
            use_dragon_tactics: 是否使用龙头战法（可选，默认使用初始化时的设置）

        Returns:
            分析结果（JSON 格式字典）
        """
        if self.llm is None:
            return self._fallback_analysis_json(symbol, price_data, technical_data)

        # 确定是否使用龙头战法
        use_dragon = use_dragon_tactics if use_dragon_tactics is not None else self.use_dragon_tactics

        # 构建上下文
        context = self._build_context(symbol, price_data, technical_data, market_context)

        # 构建提示词
        prompt = self._build_prompt(context, use_dragon_tactics=use_dragon)

        try:
            # 调用 LLM
            response = self.llm.chat(prompt, model=self.model)

            # 提取响应内容
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)

            logger.info(f"LLM 响应内容: {response_text[:500]}...")

            # 解析 JSON
            if return_json:
                if use_dragon:
                    result = self._parse_dragon_response(response_text)
                else:
                    result = self._parse_llm_response(response_text)

                result['symbol'] = symbol
                result['timestamp'] = pd.Timestamp.now()
                result['use_dragon_tactics'] = use_dragon
                return result
            else:
                return {'raw_response': response_text, 'symbol': symbol}

        except Exception as e:
            logger.error(f"LLM 调用失败: {str(e)}")
            return self._fallback_analysis_json(symbol, price_data, technical_data)

    def _build_context(self,
                      symbol: str,
                      price_data: Dict[str, Any],
                      technical_data: Dict[str, Any],
                      market_context: Optional[Dict[str, Any]]) -> str:
        """
        构建分析上下文

        Args:
            symbol: 股票代码
            price_data: 价格数据
            technical_data: 技术指标数据
            market_context: 市场上下文

        Returns:
            格式化的上下文字符串
        """
        context_parts = []

        # 基本信息
        context_parts.append(f"股票代码: {symbol}")
        context_parts.append(f"股票名称: {price_data.get('name', 'N/A')}")
        context_parts.append(f"当前价格: {price_data.get('current_price', 'N/A')}")
        context_parts.append(f"今日涨跌幅: {price_data.get('change_percent', 'N/A')}%")
        context_parts.append(f"成交量: {price_data.get('volume', 'N/A')}")

        # 🆕 竞价量比 (Call Auction Ratio)
        open_volume = price_data.get('open_volume', 0)
        prev_day_volume = price_data.get('prev_day_volume', 1)
        if open_volume > 0 and prev_day_volume > 0:
            call_auction_ratio = open_volume / prev_day_volume
            if call_auction_ratio >= 0.15:
                intensity = "极强 (主力抢筹)"
            elif call_auction_ratio >= 0.10:
                intensity = "强 (资金关注)"
            elif call_auction_ratio >= 0.05:
                intensity = "中等"
            else:
                intensity = "弱"
            context_parts.append(f"竞价抢筹度: {call_auction_ratio:.2%} ({intensity})")
        else:
            context_parts.append("竞价抢筹度: N/A")

        # 🆕 板块地位 (Sector Rank)
        sector = price_data.get('sector', 'N/A')
        sector_rank = price_data.get('sector_rank', None)
        sector_total = price_data.get('sector_total', None)
        if sector_rank is not None and sector_total is not None:
            if sector_rank == 1:
                role_desc = "👑 龙一 (板块核心龙头)"
            elif sector_rank <= 3:
                role_desc = "⭐ 前三 (板块前排)"
            elif sector_rank <= 5:
                role_desc = "中军 (板块中坚)"
            else:
                role_desc = "跟风 (板块后排)"
            context_parts.append(f"板块: {sector}")
            context_parts.append(f"板块地位: 排名 {sector_rank}/{sector_total} ({role_desc})")
        elif sector:
            context_parts.append(f"板块: {sector}")
            context_parts.append("板块地位: N/A")

        # 🆕 弱转强 (Weak to Strong)
        weak_to_strong = price_data.get('weak_to_strong', None)
        if weak_to_strong is not None:
            if weak_to_strong:
                context_parts.append("弱转强: ✅ 是 (昨天炸板/大阴，今天高开逾越压力位)")
            else:
                context_parts.append("弱转强: ❌ 否")
        else:
            context_parts.append("弱转强: N/A")

        # 🆕 分时强承接 (Intraday Support)
        intraday_support = price_data.get('intraday_support', None)
        if intraday_support is not None:
            if intraday_support:
                context_parts.append("分时强承接: ✅ 是 (股价在均线上方，下跌缩量上涨放量)")
            else:
                context_parts.append("分时强承接: ❌ 否")
        else:
            context_parts.append("分时强承接: N/A")

        # 技术指标
        context_parts.append("\n【技术指标】")

        # RSI
        rsi = technical_data.get('rsi', {})
        if rsi:
            context_parts.append(f"RSI: {rsi.get('RSI', 'N/A')}")

        # MACD
        macd = technical_data.get('macd', {})
        if macd:
            context_parts.append(f"MACD: {macd.get('Trend', 'N/A')}")
            context_parts.append(f"MACD柱: {macd.get('Histogram', 'N/A')}")

        # 布林带
        bollinger = technical_data.get('bollinger', {})
        if bollinger:
            current_price = price_data.get('current_price', 0)
            upper = bollinger.get('上轨', 0)
            lower = bollinger.get('下轨', 0)
            if upper > 0 and lower > 0:
                position = ((current_price - lower) / (upper - lower) * 100)
                context_parts.append(f"布林带位置: {position:.1f}%")

        # KDJ
        kdj = technical_data.get('kdj', {})
        if kdj:
            context_parts.append(f"KDJ: K={kdj.get('K', 'N/A')}, D={kdj.get('D', 'N/A')}, J={kdj.get('J', 'N/A')}")

        # 均线
        ma = technical_data.get('ma', {})
        if ma:
            context_parts.append(f"MA5: {ma.get('MA5', 'N/A')}")
            context_parts.append(f"MA10: {ma.get('MA10', 'N/A')}")
            context_parts.append(f"MA20: {ma.get('MA20', 'N/A')}")

        # 资金流向
        money_flow = technical_data.get('money_flow', {})
        if money_flow:
            context_parts.append(f"资金流向: {money_flow.get('资金流向', 'N/A')}")
            context_parts.append(f"主力净流入: {money_flow.get('主力净流入', 'N/A')}")

        # 市场上下文
        if market_context:
            context_parts.append("\n【市场环境】")
            context_parts.append(f"大盘指数: {market_context.get('index', 'N/A')}")
            context_parts.append(f"大盘涨跌幅: {market_context.get('index_change', 'N/A')}%")
            context_parts.append(f"市场情绪: {market_context.get('sentiment', 'N/A')}")

            # 🆕 V6.0 新增：市场情绪周期和主线识别
            market_cycle = market_context.get('market_cycle', {})
            if market_cycle:
                cycle_type = market_cycle.get('cycle', 'UNKNOWN')
                cycle_desc = market_cycle.get('description', '')
                cycle_strategy = market_cycle.get('strategy', '')
                risk_level = market_cycle.get('risk_level', 3)

                context_parts.append("\n【🌤️ 今日市场天气】")
                context_parts.append(f"市场周期: {cycle_type}")
                context_parts.append(f"周期描述: {cycle_desc}")
                context_parts.append(f"风险等级: {risk_level}/5")
                context_parts.append(f"周期策略: {cycle_strategy}")

            # 主线识别
            main_theme = market_context.get('main_theme', {})
            if main_theme:
                theme_name = main_theme.get('main_theme', '未知')
                theme_heat = main_theme.get('theme_heat', 0)
                theme_suggestion = main_theme.get('suggestion', '')

                context_parts.append("\n【🎯 今日主线】")
                context_parts.append(f"主线板块: {theme_name}")
                context_parts.append(f"主线热度: {theme_heat:.1%}")
                context_parts.append(f"主线建议: {theme_suggestion}")

        # 🆕 V12 添加预测雷达数据
        if market_context and 'highest_board' in market_context:
            current_height = market_context.get('highest_board', 0)
            prob = self.pe.get_promotion_probability(current_height)
            pivot = self.pe.detect_sentiment_pivot()
            
            prob_display = f"{prob}%" if prob >= 0 else "数据不足"
            context_parts.append("\n【🔮 预测雷达数据】")
            context_parts.append(f"历史同高度晋级成功率: {prob_display}")
            context_parts.append(f"情绪转折点预判: {pivot['action']} (原因: {pivot['reason']})")

        return "\n".join(context_parts)

    def _build_prompt(self, context: str, use_dragon_tactics: bool = False) -> str:
        """
        构建 LLM 提示词（强制 JSON 输出）

        Args:
            context: 上下文字符串
            use_dragon_tactics: 是否使用龙头战法 Prompt

        Returns:
            完整的提示词
        """
        if use_dragon_tactics:
            # --- 🛡️ V3.0 新增：前置硬规则过滤 (Hard Rules) ---
            # 动态生成特殊指令
            special_instructions = ""

            # 检测 ST/*ST
            if "ST" in context or "*ST" in context:
                special_instructions += """
🚨🚨🚨 触发生死红线规则 🚨🚨🚨
严重警告：检测到该股为 ST/退市风险股。
【强制执行】：
1. 评分不得超过 10 分
2. role 必须为 "杂毛"
3. signal 必须为 "SELL" 或 "WAIT"
4. reason 必须包含 "退市风险" 或 "流动性风险"
5. suggested_position 必须为 0.0

除非有明确的"摘帽"内幕逻辑，否则一律视为【垃圾】，直接【🔴跑】。
有命赚没命花，本金安全第一！
"""

            # 检测创业板/科创板（20cm）
            if "300" in context or "688" in context:
                special_instructions += """
⚡ 波动率提示：这是 20cm 标的（创业板/科创板）。
【强制执行】：
1. 涨停判断标准：涨幅 >= 19.8% 才算封板
2. 涨幅 10%-15% 属于"烂板"或"严重分歧"，必须扣分
3. 涨幅 < 8% 不算强势，直接给低分
4. 严禁将 13% 的涨幅误判为"涨停板"
"""

            # 使用 V3.0 龙头暴力版 Prompt
            prompt = f"""【角色定义】
你不是传统的价值投资者，也不是看教科书的技术分析师。
你是A股顶级游资操盘手。你的唯一目标是：捕捉市场最强龙头的加速段。
你的信条："龙头多一条命"、"强者恒强"、"分歧是买点，一致是卖点"。

【🆕 V6.0 核心升级：具备"大局观"的指挥官】
你现在不仅是个技术分析高手，更是一个懂人性的市场指挥官。
你必须根据【今日市场天气】和【今日主线】来调整你的策略：

🌤️ 市场天气策略：
- 🚀 主升期：情绪高涨，满仓猛干，龙头战法，不要怂！
- 🔥 高潮期：情绪极度高涨，风险极大，只卖不买，果断止盈！
- 📉 退潮期：退潮明显，只卖不买，清仓观望，等待周期切换！
- 🌊 混沌期：情绪震荡，空仓或轻仓套利，控制仓位！
- 🧊 冰点期：情绪冰点，试错首板，做新题材，小仓位试探！

【🆕 V6.1 特种作战：ICE/DECLINE 周期的逆势暴利模式】
在 🧊 冰点期 和 📉 退潮期，除了常规的"只卖不买"，还有两个暴利机会：

🎯 反核按钮模式（ANTI_NUCLEAR）：
- 适用场景：核心龙头被核按钮按到跌停
- 识别信号：跌停板上出现大单翘板（Order Imbalance 剧烈变化）
- 操作策略：博弈地天板，关注盘口变化
- 风险提示：高风险，小仓位博弈，严格止损

🐉 龙回头模式（DRAGON_RETURN）：
- 适用场景：真龙第一波断板后的第 3-5 天
- 识别信号：龙头首日断板大跌（-5% ~ -10%），且未破 10 日线
- 操作策略：均线企稳时的低吸机会
- 胜率提示：胜率极高，是游资的经典战法

决策标准更新（包含特种作战）：
- 🧊 冰点期 + ⭐⭐⭐ 真龙 + 跌停板 + 大单翘板 → 🟢 反核博弈（小仓位）
- 🧊 冰点期 + ⭐⭐⭐ 真龙 + 首阴大跌 + 未破10日线 → 🟢 龙回头低吸（小仓位）
- 📉 退潮期 + ⭐⭐⭐ 真龙 + 跌停板 + 大单翘板 → 🟢 反核博弈（极小仓位）
- 📉 退潮期 + ⭐⭐⭐ 真龙 + 首阴大跌 + 未破10日线 → 🟢 龙回头低吸（极小仓位）
- 其他情况按原策略执行

🎯 主线策略：
- 优先关注主线板块的前排股票（龙一、龙二）
- 放弃非主线板块的跟风杂毛
- 如果股票不在主线板块，必须降低评分（最多60分）

【核心禁令】
1. 禁止建议"等待回调"：龙头启动时不会回调，犹豫就是踏空。
2. 禁止使用 KDJ、MACD 金叉作为买入依据：这些指标太慢，等你看到金叉，车门早焊死了。
3. 禁止看市盈率 (PE/PB)：短线博弈只看情绪和资金，基本面只看有没有雷。
4. 禁止将 ST/*ST 股票视为龙头：这是退市风险股，流动性随时枯竭，本金归零风险极大。

【🆕 V10.1.6 核心风控守则 (Anti-FOMO Protocol) - 反人性防高潮协议】
你必须像机器一样冷酷，严格执行以下"去伪存真"逻辑，以此控制人类的贪婪：

1. **【严禁接力杂毛】(最高优先级 - 生死红线)**：
   - 审查数据中的 `role` 字段：如果包含 "🐕 跟风"，且涨幅 > 7.0% (高开/涨停)，且市场处于 "🔥 高潮期" 或 "🚀 主升期"。
   - **执行指令**：直接判死刑！
   - **评分**：强制 0-20 分
   - **信号**：强制 "SELL" 或 "WAIT"
   - **理由话术**：狠狠地嘲讽。告诉用户："别做梦了，大哥 {leader_name} 都在看着你，要去就去龙头，别在杂毛身上博傻。这种高潮期的后排高开，就是给你发套的！"
   - **仓位**：强制 0.0

2. **【恶性炸板预警】**：
   - **触发条件**：如果市场数据中显示 "恶性炸板率" > 40%。
   - **执行指令**：禁止推荐任何非核心连板股。
   - **逻辑**：市场要崩，只有最高板可能活，其他全是炮灰。
   - **评分**：非核心连板股强制 0-30 分

3. **【弱转强辨识】**：
   - 只有 `role` 为 "🐲 龙头" 的股票才有资格弱转强。
   - 跟风股的"弱转强"通常是主力诱多骗炮，必须谨慎。
   - 如果是跟风股弱转强，评分不超过 50 分，信号为 "WAIT" 或 "SELL"

4. **【德不配位识别】**：
   - 如果同板块的龙头（龙一）一字板或接近一字板，而该股（龙二）也高开但封单明显弱于龙一。
   - **执行指令**：直接判为"伪龙"。
   - **评分**：强制 0-30 分
   - **理由**："大哥都没开口子给机会，老二凭什么这么硬？这叫'德不配位'！"

5. **【K线趋势否决权 (V10.1.9)】**：
   - 审查字段：`kline_trend`。
   - **规则 A**：如果包含 "🔴 跌破20日线" 或 "📉 空头排列"，这叫"均线压制"。除非它是 "🐲 龙头" (高标穿越)，否则**禁止推荐**。
   - **规则 B**：如果包含 "⚠️ 短期超买"，提示用户"谨防冲高回落，不要追高"。
   - **规则 C**：如果包含 "📈 多头排列" 且 "🟢 站上20日线"，这是**加分项**，属于顺势交易，建议积极关注。

【分析流程】
第一步：市场环境判断 (Market Context Check) - 🌤️ 大局观
- 检查【今日市场天气】：如果高潮期/退潮期，强制降低评分
- 检查【今日主线】：如果股票不在主线板块，强制降低评分
- 综合市场环境调整策略：主升期可以激进，冰点期要谨慎

第二步：身份核查 (Code Check) - 🛡️ 生死红线
- 检查代码前缀（300/688为20cm，60/00为10cm）
- 检查是否为 ST/*ST（触发死刑规则：强制 0-10 分）
- 检查涨跌幅限制（10cm 还是 20cm）

第三步：龙头辨识度 (The "One" Factor)
- 它是唯一的吗？（板块内唯一涨停/最高板）
- 它是最早的吗？（率先上板，带动板块）
- 它有伴吗？（板块内有3只以上涨停助攻）
- 板块地位：龙一(板块核心龙头)、前三(板块前排)、中军(板块中坚)、跟风(板块后排)

第四步：资金微观结构 (盘口语言)
- 竞价抢筹度：9:25分成交量 / 昨天全天成交量
  - 极强 (>=15%)：主力抢筹，猛干
  - 强 (>=10%)：资金关注，可以干
  - 中等 (>=5%)：一般
  - 弱 (<5%)：不关注
- 弱转强：昨天炸板/大阴线，今天高开逾越压力位（最强买点）
- 分时强承接：股价在均线上方运行，下跌缩量，上涨放量（资金护盘）
- 对于 20cm 标的：涨幅 > 10% 且不回落是加速信号，不是卖点！

第五步：最终决策矩阵 (Execution)
根据以下维度评分并输出决策：
- 市场环境匹配度（20%）：是否在主线板块 + 市场周期是否支持
- 龙头地位（30%）：板块排名 + 身位领先
- 竞价强度（20%）：竞价抢筹度
- 弱转强形态（15%）：弱转强信号
- 分时承接（15%）：分时强承接

决策标准（必须结合市场天气）：
- 🚀 主升期 + ⭐⭐⭐ 真龙 + 爆量/弱转强 + 涨幅>10% → 🟢 扫板/排板 (满仓/重仓)
- 🚀 主升期 + ⭐⭐⭐ 真龙 + 烂板/分歧 + 涨幅<5% → 🟡 低吸博弈 (半仓)
- 🧊 冰点期 + ⭐⭐⭐ 真龙 + 率先上板 → 🟢 试错首板 (小仓位)
- 🔥 高潮期 + 任意 → 🔴 只卖不买 (0)
- 📉 退潮期 + 任意 → 🔴 只卖不买 (0)
- 🌊 混沌期 + ⭐⭐ 中军/支线 + 图形漂亮 → 🟢 打板/跟随 (轻仓)
- ⭐⭐⭐ 真龙 + 不在主线板块 → 🔵 只看不买 (0)
- ⭐ 跟风 + 任意 → 🔵 只看不买 (0)
- ❌ 杂毛 + 任意 → 🔴 清仓/核按钮 (0)

{special_instructions}

【当前数据】
{context}

【输出格式】
请务必只返回标准的 JSON 格式，不要包含 markdown 标记或其他文字：
{{
    "score": [0-100的评分, 龙头股必须给85分以上],
    "role": "龙头" | "中军" | "跟风" | "杂毛",
    "signal": "BUY_AGGRESSIVE" (猛干) | "BUY_DIP" (低吸) | "WAIT" (观望) | "SELL" (跑),
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "reason": "简短理由，例如：'AI眼镜核心龙头，20cm突破平台，竞价爆量弱转强，KDJ失效不看，直接扫板'",
    "stop_loss_price": [具体止损价]
}}

注意：
1. 只输出 JSON，不要有任何其他文字
2. score: 0-100，龙头股必须给85分以上
3. signal: BUY_AGGRESSIVE(猛干), BUY_DIP(低吸), WAIT(观望), SELL(跑)
4. role: 龙头/中军/跟风/杂毛
5. confidence: HIGH/MEDIUM/LOW
6. stop_loss_price: 具体止损价
"""
        else:
            # 使用标准 Prompt
            prompt = f"""你是一个量化交易决策系统。请基于以下数据分析该股票：

{context}

请务必只返回标准的 JSON 格式，不要包含 markdown 标记或其他文字。格式如下：
{{
    "score": 0-100之间的整数,
    "signal": "BUY" | "SELL" | "HOLD",
    "risk_level": "LOW" | "MEDIUM" | "HIGH",
    "reason": "简短理由(50字内)",
    "suggested_position": 0.0-1.0之间的建议仓位
}}

注意：
1. 只输出 JSON，不要有任何其他文字
2. score: 0-100，越高越看好
3. signal: BUY(买入), SELL(卖出), HOLD(观望)
4. risk_level: LOW(低风险), MEDIUM(中风险), HIGH(高风险)
5. suggested_position: 0.0-1.0，建议仓位比例
"""
        return prompt

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析 LLM 返回的 JSON 响应

        Args:
            response_text: LLM 返回的文本

        Returns:
            解析后的字典
        """
        import re
        try:
            # 尝试清洗 markdown 标记 (```json ... ```)
            cleaned = re.sub(r'```json\s*|\s*```', '', response_text).strip()
            result = json.loads(cleaned)

            # 验证必需字段
            required_fields = ['score', 'signal', 'risk_level', 'reason', 'suggested_position']
            for field in required_fields:
                if field not in result:
                    logger.warning(f"缺少必需字段: {field}")
                    result[field] = self._get_default_value(field)

            # 验证数据类型
            if not isinstance(result['score'], (int, float)):
                result['score'] = 50
            if result['signal'] not in ['BUY', 'SELL', 'HOLD']:
                result['signal'] = 'HOLD'
            if result['risk_level'] not in ['LOW', 'MEDIUM', 'HIGH']:
                result['risk_level'] = 'MEDIUM'
            if not isinstance(result['suggested_position'], (int, float)):
                result['suggested_position'] = 0.5

            return result

        except Exception as e:
            logger.error(f"JSON 解析失败: {e}")
            # 返回兜底数据
            return {
                "score": 50,
                "signal": "HOLD",
                "risk_level": "HIGH",
                "reason": "解析失败",
                "suggested_position": 0.0
            }

    def _get_default_value(self, field: str) -> Any:
        """获取字段的默认值"""
        defaults = {
            'score': 50,
            'signal': 'HOLD',
            'risk_level': 'MEDIUM',
            'reason': '数据不足',
            'suggested_position': 0.0
        }
        return defaults.get(field, None)

    def _parse_dragon_response(self, response_text: str) -> Dict[str, Any]:
        """解析龙头战法 LLM 响应"""
        import re
        try:
            logger.debug(f"LLM 原始响应: {response_text[:500]}...")
            cleaned = re.sub(r'```json\s*|\s*```', '', response_text).strip()
            logger.debug(f"清洗后的响应: {cleaned[:500]}...")
            result = json.loads(cleaned)

            # 验证必需字段
            required_fields = ['score', 'role', 'signal', 'confidence', 'reason', 'stop_loss_price']
            for field in required_fields:
                if field not in result:
                    logger.warning(f"缺少必需字段: {field}")
                    result[field] = self._get_dragon_default_value(field)

            # 验证数据类型
            if not isinstance(result['score'], (int, float)):
                result['score'] = 50
            if result['role'] not in ['龙头', '中军', '跟风', '杂毛']:
                result['role'] = '跟风'
            if result['signal'] not in ['BUY_AGGRESSIVE', 'BUY_DIP', 'WAIT', 'SELL']:
                result['signal'] = 'WAIT'
            if result['confidence'] not in ['HIGH', 'MEDIUM', 'LOW']:
                result['confidence'] = 'MEDIUM'

            return result

        except Exception as e:
            logger.error(f"JSON 解析失败: {e}")
            # 返回兜底数据
            return {
                "score": 50,
                "role": "跟风",
                "signal": "WAIT",
                "confidence": "MEDIUM",
                "reason": "解析失败",
                "stop_loss_price": 0
            }

    def _get_dragon_default_value(self, field: str) -> Any:
        """获取龙头战法字段的默认值"""
        defaults = {
            'score': 50,
            'role': '跟风',
            'signal': 'WAIT',
            'confidence': 'MEDIUM',
            'reason': '数据不足',
            'stop_loss_price': 0
        }
        return defaults.get(field, None)

    def _fallback_analysis_json(self,
                                symbol: str,
                                price_data: Dict[str, Any],
                                technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        降级分析（返回 JSON 格式）

        Args:
            symbol: 股票代码
            price_data: 价格数据
            technical_data: 技术指标数据

        Returns:
            JSON 格式的分析结果
        """
        # 计算综合得分
        score = 0

        # 涨跌幅
        change = price_data.get('change_percent', 0)
        if change > 5:
            score += 20
        elif change > 0:
            score += 10
        elif change > -3:
            score += 5

        # RSI
        rsi = technical_data.get('rsi', {}).get('RSI', 50)
        if rsi < 30:
            score += 15
        elif rsi > 70:
            score -= 10
        elif 40 <= rsi <= 60:
            score += 10

        # MACD
        macd_trend = technical_data.get('macd', {}).get('Trend', '')
        if macd_trend == '多头':
            score += 15
        elif macd_trend == '空头':
            score -= 15

        # 资金流向
        money_flow = technical_data.get('money_flow', {}).get('资金流向', '')
        if money_flow == '大幅流入':
            score += 20
        elif money_flow == '流入':
            score += 10
        elif money_flow == '流出':
            score -= 10

        # 生成信号
        if score >= 50:
            signal = 'BUY'
            risk_level = 'LOW' if score >= 70 else 'MEDIUM'
        elif score >= 30:
            signal = 'HOLD'
            risk_level = 'MEDIUM'
        else:
            signal = 'SELL'
            risk_level = 'HIGH'

        return {
            'score': min(max(score, 0), 100),
            'signal': signal,
            'risk_level': risk_level,
            'reason': '规则分析',
            'suggested_position': min(score / 100, 1.0)
        }

    def _fallback_analysis(self,
                          symbol: str,
                          price_data: Dict[str, Any],
                          technical_data: Dict[str, Any]) -> str:
        """
        降级分析（当 LLM 不可用时使用简化规则）

        Args:
            symbol: 股票代码
            price_data: 价格数据
            technical_data: 技术指标数据

        Returns:
            简化分析报告
        """
        # 计算综合得分
        score = 0
        signals = []

        # 涨跌幅
        change = price_data.get('change_percent', 0)
        if change > 5:
            score += 20
            signals.append("强势上涨")
        elif change > 0:
            score += 10
            signals.append("小幅上涨")
        elif change > -3:
            score += 5
            signals.append("小幅下跌")
        else:
            signals.append("大幅下跌")

        # RSI
        rsi = technical_data.get('rsi', {}).get('RSI', 50)
        if rsi < 30:
            score += 15
            signals.append("RSI超卖")
        elif rsi > 70:
            score -= 10
            signals.append("RSI超买")
        elif 40 <= rsi <= 60:
            score += 10
            signals.append("RSI中性")

        # MACD
        macd_trend = technical_data.get('macd', {}).get('Trend', '')
        if macd_trend == '多头':
            score += 15
            signals.append("MACD多头")
        elif macd_trend == '空头':
            score -= 15
            signals.append("MACD空头")

        # 资金流向
        money_flow = technical_data.get('money_flow', {}).get('资金流向', '')
        if money_flow == '大幅流入':
            score += 20
            signals.append("资金大幅流入")
        elif money_flow == '流入':
            score += 10
            signals.append("资金流入")
        elif money_flow == '流出':
            score -= 10
            signals.append("资金流出")

        # 生成建议
        if score >= 50:
            suggestion = "买入"
        elif score >= 30:
            suggestion = "观望"
        else:
            suggestion = "卖出"

        # 格式化输出
        report = f"""━━━━━━━━━━━━━━━━━━━━━━━━
【情绪评分】
{min(max(score, 0), 100)}分

【技术面分析】
{', '.join(signals)}

【潜在风险】
市场波动风险

【操作建议】
{suggestion}

【理由】
基于技术指标综合评分
━━━━━━━━━━━━━━━━━━━━━━━━

*注：当前使用简化规则分析，配置 LLM API 后可获得更智能的分析*"""

        return report

    def batch_analyze(self,
                     stocks: List[Dict[str, Any]],
                     market_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """
        批量分析股票（同步方式）

        Args:
            stocks: 股票列表，每个元素包含 symbol, price_data, technical_data
            market_context: 市场上下文

        Returns:
            分析结果列表
        """
        results = []

        for stock in stocks:
            try:
                analysis = self.analyze_stock(
                    symbol=stock['symbol'],
                    price_data=stock['price_data'],
                    technical_data=stock['technical_data'],
                    market_context=market_context
                )

                results.append({
                    'symbol': stock['symbol'],
                    'analysis': analysis,
                    'timestamp': pd.Timestamp.now()
                })

            except Exception as e:
                logger.error(f"分析股票 {stock['symbol']} 失败: {str(e)}")
                results.append({
                    'symbol': stock['symbol'],
                    'analysis': f"分析失败: {str(e)}",
                    'timestamp': pd.Timestamp.now()
                })

        return results

    async def async_batch_analyze(self,

                                       stocks: List[Dict[str, Any]],

                                       market_context: Optional[Dict[str, Any]] = None,

                                       max_concurrent: int = 10,

                                       use_sentiment_monitor: bool = True) -> List[Dict[str, Any]]:

            """

            异步批量分析股票（高性能）

            

            Args:

                stocks: 股票列表，每个元素包含 symbol, price_data, technical_data

                market_context: 市场上下文

                max_concurrent: 最大并发数

                use_sentiment_monitor: 是否使用情绪监控（默认 True）

                

            Returns:

                分析结果列表（JSON 格式）

            """

            import asyncio

            

            # 情绪监控：检查市场结构

            sentiment_result = None

            if use_sentiment_monitor and self.dragon_tactics:

                try:

                    from logic.market_sentiment_monitor import MarketSentimentMonitor, CircuitBreaker

                    

                    monitor = MarketSentimentMonitor()

                    breaker = CircuitBreaker(monitor)

                    

                    # 检查市场结构

                    stocks_with_scores = []

                    for stock in stocks:

                        # 临时评分（这里可以先用规则评分，或者等分析完成后再评分）

                        stocks_with_scores.append({

                            'symbol': stock['symbol'],

                            'score': 50,  # 临时评分，后续会更新

                            'change_percent': stock.get('price_data', {}).get('change_percent', 0),

                            'amount': stock.get('price_data', {}).get('amount', 0)

                        })

                    

                    breaker_result = breaker.check_and_break(stocks_with_scores)

                    sentiment_result = breaker_result['market_structure']

                    

                    # 如果触发熔断，返回警告

                    if breaker_result['is_triggered']:

                        logger.warning(f"⚠️ 情绪熔断触发：{breaker_result['trigger_reason']}")

                        logger.warning(f"市场状态：{sentiment_result['market_state']}")

                        logger.warning("停止开仓，建议观望")

                        

                        # 返回警告信息

                        return [{

                            'symbol': 'MARKET_WARNING',

                            'score': 0,

                            'signal': 'WAIT',

                            'confidence': 'HIGH',

                            'reason': f"情绪熔断：{breaker_result['trigger_reason']}",

                            'market_state': sentiment_result['market_state'],

                            'market_warning': True,

                            'timestamp': pd.Timestamp.now()

                        }]

                    

                except ImportError:

                    logger.warning("无法导入 MarketSentimentMonitor，情绪监控功能不可用")

            

            async def analyze_single(stock):

                """分析单只股票"""

                try:

                    result = self.analyze_stock(

                        symbol=stock['symbol'],

                        price_data=stock['price_data'],

                        technical_data=stock['technical_data'],

                        market_context=market_context,

                        return_json=True

                    )

                    return result

                except Exception as e:

                    logger.error(f"分析股票 {stock['symbol']} 失败: {str(e)}")

                    return {

                        'symbol': stock['symbol'],

                        'score': 50,

                        'signal': 'HOLD',

                        'risk_level': 'HIGH',

                        'reason': f"分析失败: {str(e)}",

                        'suggested_position': 0.0,

                        'timestamp': pd.Timestamp.now()

                    }

    

            # 创建信号量控制并发

            semaphore = asyncio.Semaphore(max_concurrent)

    

            async def analyze_with_semaphore(stock):

                async with semaphore:

                    # 模拟异步（实际 LLM 调用可能是同步的）

                    return await asyncio.get_event_loop().run_in_executor(

                        None, lambda: asyncio.create_task(analyze_single(stock)))

            # 执行批量分析
            tasks = [analyze_single(stock) for stock in stocks]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            formatted_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"股票 {stocks[i]['symbol']} 分析异常: {str(result)}")
                    formatted_results.append({
                        'symbol': stocks[i]['symbol'],
                        'score': 50,
                        'signal': 'HOLD',
                        'risk_level': 'HIGH',
                        'reason': f"异常: {str(result)}",
                        'suggested_position': 0.0,
                        'timestamp': pd.Timestamp.now()
                    })
                else:
                    formatted_results.append(result)

            return formatted_results


class RuleBasedAgent:
    """
    规则代理（保留用于快速分析）
    基于简化规则的快速分析
    """

    def __init__(self):
        """初始化规则代理"""
        pass

    def analyze_stock(self,
                     symbol: str,
                     price_data: Dict[str, Any],
                     technical_data: Dict[str, Any]) -> str:
        """
        基于规则分析股票

        Args:
            symbol: 股票代码
            price_data: 价格数据
            technical_data: 技术指标数据

        Returns:
            分析报告
        """
        # 计算各项指标得分
        scores = self._calculate_scores(price_data, technical_data)

        # 判断市场状态
        market_state = self._judge_market_state(scores, price_data)

        # 识别风险点
        risks = self._identify_risks(technical_data, scores)

        # 生成操作建议
        operation = self._generate_operation(scores, market_state, risks, technical_data)

        # 组装分析报告
        report = self._format_report(symbol, technical_data, market_state, risks, operation)

        return report

    def _calculate_scores(self, price_data: Dict[str, Any], technical_data: Dict[str, Any]) -> Dict[str, int]:
        """计算各项技术指标的得分"""
        scores = {}

        # 涨跌幅得分
        change = price_data.get('change_percent', 0)
        if change > 5:
            scores['涨跌幅'] = 20
        elif change > 3:
            scores['涨跌幅'] = 15
        elif change > 0:
            scores['涨跌幅'] = 10
        elif change > -3:
            scores['涨跌幅'] = 5
        else:
            scores['涨跌幅'] = 0

        # MACD 得分
        macd = technical_data.get('macd', {})
        if macd.get('Trend') == '多头':
            scores['MACD'] = 20
        elif macd.get('Trend') == '空头':
            scores['MACD'] = 0
        else:
            scores['MACD'] = 10

        # RSI 得分
        rsi = technical_data.get('rsi', {})
        rsi_value = rsi.get('RSI', 50)
        if 30 <= rsi_value <= 70:
            scores['RSI'] = 20
        elif rsi_value < 30:
            scores['RSI'] = 15  # 超卖，可能反弹
        elif rsi_value > 70:
            scores['RSI'] = 5   # 超买，风险高
        else:
            scores['RSI'] = 10

        # 布林带得分
        bollinger = technical_data.get('bollinger', {})
        current_price = price_data.get('current_price', 0)
        lower_band = bollinger.get('下轨', 0)
        upper_band = bollinger.get('上轨', 0)

        if lower_band > 0 and upper_band > 0:
            position = (current_price - lower_band) / (upper_band - lower_band) * 100
            if position < 20:
                scores['布林带'] = 20  # 接近下轨
            elif position > 80:
                scores['布林带'] = 5   # 接近上轨
            else:
                scores['布林带'] = 15  # 中间区域
        else:
            scores['布林带'] = 10

        # 资金流向得分
        money_flow = technical_data.get('money_flow', {})
        flow_type = money_flow.get('资金流向', '')

        if flow_type == '大幅流入':
            scores['资金流向'] = 20
        elif flow_type == '流入':
            scores['资金流向'] = 15
        elif flow_type == '流出':
            scores['资金流向'] = 5
        else:
            scores['资金流向'] = 10

        # KDJ 得分
        kdj = technical_data.get('kdj', {})
        k_value = kdj.get('K', 50)
        d_value = kdj.get('D', 50)

        if k_value < 20 and d_value < 20:
            scores['KDJ'] = 20  # 超卖
        elif k_value > 80 and d_value > 80:
            scores['KDJ'] = 5   # 超买
        elif k_value > d_value:
            scores['KDJ'] = 15  # 金叉
        else:
            scores['KDJ'] = 10

        return scores

    def _judge_market_state(self, scores: Dict[str, int], price_data: Dict[str, Any]) -> str:
        """判断市场状态"""
        total_score = sum(scores.values())

        if total_score >= 80:
            return "强势"
        elif total_score >= 60:
            return "偏强"
        elif total_score >= 40:
            return "震荡"
        elif total_score >= 20:
            return "偏弱"
        else:
            return "弱势"

    def _identify_risks(self, technical_data: Dict[str, Any], scores: Dict[str, int]) -> List[str]:
        """识别风险点"""
        risks = []

        # RSI 超买风险
        rsi = technical_data.get('rsi', {}).get('RSI', 50)
        if rsi > 80:
            risks.append("RSI严重超买，短期回调风险高")

        # MACD 顶背离风险
        macd = technical_data.get('macd', {})
        if macd.get('Trend') == '空头':
            risks.append("MACD进入空头趋势，注意风险")

        # 布林带上轨风险
        bollinger = technical_data.get('bollinger', {})
        current_price = technical_data.get('current_price', 0)
        upper_band = bollinger.get('上轨', 0)

        if upper_band > 0 and current_price > upper_band:
            risks.append("价格突破布林带上轨，谨防回调")

        # 资金流出风险
        money_flow = technical_data.get('money_flow', {}).get('资金流向', '')
        if money_flow == '流出' or money_flow == '大幅流出':
            risks.append("资金持续流出，需谨慎")

        if not risks:
            risks.append("无明显风险信号")

        return risks

    def _generate_operation(self,
                           scores: Dict[str, int],
                           market_state: str,
                           risks: List[str],
                           technical_data: Dict[str, Any]) -> str:
        """生成操作建议"""
        total_score = sum(scores.values())

        # 检查是否有严重风险
        severe_risks = [r for r in risks if '严重' in r or '高' in r]

        if severe_risks:
            return "卖出（风险较高）"

        if total_score >= 80:
            return "买入"
        elif total_score >= 60:
            return "轻仓买入"
        elif total_score >= 40:
            return "观望"
        elif total_score >= 20:
            return "减仓"
        else:
            return "回避"

    def _format_report(self,
                      symbol: str,
                      technical_data: Dict[str, Any],
                      market_state: str,
                      risks: List[str],
                      operation: str) -> str:
        """格式化分析报告"""
        report = f"""━━━━━━━━━━━━━━━━━━━━━━━━
【股票】{symbol}

【市场状态】{market_state}

【技术指标】
- RSI: {technical_data.get('rsi', {}).get('RSI', 'N/A')}
- MACD: {technical_data.get('macd', {}).get('Trend', 'N/A')}
- 布林带: {technical_data.get('bollinger', {}).get('Trend', 'N/A')}
- 资金流向: {technical_data.get('money_flow', {}).get('资金流向', 'N/A')}

【风险提示】
{chr(10).join([f'• {r}' for r in risks])}

【操作建议】
{operation}
━━━━━━━━━━━━━━━━━━━━━━━━

*注：当前使用规则分析，配置 LLM API 可获得更智能的分析*"""

        return report


class DragonAIAgent:
    """
    龙头战法 AI 代理（V3.0 暴力版）
    专门用于捕捉市场最强龙头的加速段
    """
    
    def __init__(self, api_key: str, provider: str = 'openai', model: str = 'gpt-4'):
        """
        初始化龙头战法 AI 代理
        
        Args:
            api_key: API 密钥
            provider: 提供商
            model: 模型名称
        """
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.llm = self._init_llm()
        
        # 初始化龙头战法分析器
        try:
            from logic.dragon_tactics import DragonTactics
            self.dragon_tactics = DragonTactics()
        except ImportError:
            logger.warning("无法导入 DragonTactics")
            self.dragon_tactics = None
    
    def _init_llm(self):
        """初始化 LLM 接口"""
        try:
            from logic.llm_interface import DeepSeekProvider, OpenAIProvider

            # 根据提供商选择对应的类
            if self.provider == 'deepseek':
                return DeepSeekProvider(api_key=self.api_key)
            elif self.provider == 'openai':
                return OpenAIProvider(api_key=self.api_key)
            else:
                # 默认使用 DeepSeek
                return DeepSeekProvider(api_key=self.api_key)
        except ImportError:
            logger.error("无法导入 LLM 接口")
            return None
    
    def analyze_stock_dragon(self,
                            symbol: str,
                            price_data: Dict[str, Any],
                            technical_data: Dict[str, Any],
                            auction_data: Optional[Dict[str, Any]] = None,
                            sector_data: Optional[Dict[str, Any]] = None,
                            kline_data: Optional[pd.DataFrame] = None,
                            intraday_data: Optional[pd.DataFrame] = None,
                            name: str = '') -> Dict[str, Any]:
        """
        使用龙头战法分析股票

        Args:
            symbol: 股票代码
            price_data: 价格数据
            technical_data: 技术指标数据
            auction_data: 竞价数据（可选）
            sector_data: 板块数据（可选）
            kline_data: K线数据（可选）
            intraday_data: 分时数据（可选）
            name: 股票名称（可选，用于检测 ST 标志）

        Returns:
            分析结果（JSON 格式）
        """
        if self.llm is None:
            return self._fallback_dragon_analysis(symbol, price_data, technical_data)

        # 1. 代码前缀检查（包括 ST 检查）
        code_check = self.dragon_tactics.check_code_prefix(symbol, name) if self.dragon_tactics else {}
        if code_check.get('banned', False):
            return {
                'score': 0,
                'role': '杂毛',
                'signal': 'SELL',
                'confidence': 'HIGH',
                'reason': code_check.get('banned_reason', '禁止交易'),
                'stop_loss_price': price_data.get('current_price', 0)
            }
        
        # 2. 竞价分析
        auction_analysis = {}
        if auction_data and self.dragon_tactics:
            auction_analysis = self.dragon_tactics.analyze_call_auction(
                auction_data.get('open_volume', 0),
                auction_data.get('prev_day_volume', 1),
                auction_data.get('open_amount', 0),
                auction_data.get('prev_day_amount', 1)
            )
        
        # 3. 板块地位分析
        sector_analysis = {}
        if sector_data and self.dragon_tactics:
            sector_analysis = self.dragon_tactics.analyze_sector_rank(
                symbol,
                sector_data.get('sector', ''),
                price_data.get('change_percent', 0),
                sector_data.get('sector_stocks'),
                sector_data.get('limit_up_count', 0)
            )
        
        # 4. 弱转强分析
        weak_to_strong_analysis = {}
        if kline_data is not None and self.dragon_tactics:
            weak_to_strong_analysis = self.dragon_tactics.analyze_weak_to_strong(kline_data)
        
        # 5. 分时承接分析
        intraday_support_analysis = {}
        if intraday_data is not None and self.dragon_tactics:
            intraday_support_analysis = self.dragon_tactics.analyze_intraday_support(intraday_data)
        
        # 6. 决策矩阵
        decision = {}
        if self.dragon_tactics:
            decision = self.dragon_tactics.make_decision_matrix(
                sector_analysis.get('role_score', 0),
                auction_analysis.get('auction_score', 0),
                weak_to_strong_analysis.get('weak_to_strong_score', 0),
                intraday_support_analysis.get('intraday_support_score', 0),
                price_data.get('change_percent', 0),
                code_check.get('max_limit', 10) == 20
            )
        
        # 7. 构建上下文
        context = self._build_dragon_context(
            symbol, price_data, technical_data,
            auction_analysis, sector_analysis,
            weak_to_strong_analysis, intraday_support_analysis,
            code_check
        )
        
        # 8. 构建提示词（V3.0 暴力版）
        prompt = self._build_dragon_prompt(context)
        
        try:
            # 调用 LLM
            response = self.llm.chat(prompt, model=self.model)

            # 提取响应内容
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)

            logger.info(f"LLM 响应内容: {response_text[:500]}...")

            # 解析 JSON
            result = self._parse_dragon_response(response_text)

            # 合并决策矩阵的结果
            result.update({
                'symbol': symbol,
                'timestamp': pd.Timestamp.now(),
                'code_prefix': code_check.get('prefix_type', '未知'),
                'is_20cm': code_check.get('max_limit', 10) == 20,
                'auction_intensity': auction_analysis.get('auction_intensity', '未知'),
                'sector_role': sector_analysis.get('role', '未知'),
                'sector_heat': sector_analysis.get('sector_heat', '未知')
            })

            return result

        except Exception as e:
            logger.error(f"LLM 调用失败: {str(e)}")
            # 返回决策矩阵的结果
            return {
                'score': decision.get('total_score', 50),
                'role': decision.get('role', '未知'),
                'signal': decision.get('signal', 'WAIT'),
                'confidence': decision.get('confidence', 'MEDIUM'),
                'reason': decision.get('reason', 'LLM分析失败，使用规则决策'),
                'stop_loss_price': price_data.get('current_price', 0) * 0.95,
                'symbol': symbol,
                'timestamp': pd.Timestamp.now()
            }
    
    def _build_dragon_context(self,
                             symbol: str,
                             price_data: Dict[str, Any],
                             technical_data: Dict[str, Any],
                             auction_analysis: Dict[str, Any],
                             sector_analysis: Dict[str, Any],
                             weak_to_strong_analysis: Dict[str, Any],
                             intraday_support_analysis: Dict[str, Any],
                             code_check: Dict[str, Any]) -> str:
        """构建龙头战法上下文"""
        context_parts = []
        
        # 基本信息
        context_parts.append(f"股票代码: {symbol}")
        context_parts.append(f"当前价格: {price_data.get('current_price', 'N/A')}")
        context_parts.append(f"今日涨跌幅: {price_data.get('change_percent', 'N/A')}%")
        context_parts.append(f"赛道: {code_check.get('prefix_type', '未知')}")
        
        # 竞价数据
        if auction_analysis:
            context_parts.append(f"\n【竞价数据】")
            context_parts.append(f"竞价抢筹度: {auction_analysis.get('call_auction_ratio', 0):.2%}")
            context_parts.append(f"竞价强度: {auction_analysis.get('auction_intensity', '未知')}")
        
        # 板块地位
        if sector_analysis:
            context_parts.append(f"\n【板块地位】")
            context_parts.append(f"板块: {sector_analysis.get('sector', '未知')}")
            context_parts.append(f"角色: {sector_analysis.get('role', '未知')}")
            context_parts.append(f"板块热度: {sector_analysis.get('sector_heat', '未知')}")
            if 'rank_in_sector' in sector_analysis:
                context_parts.append(f"板块排名: {sector_analysis['rank_in_sector']}/{sector_analysis['total_stocks_in_sector']}")
        
        # 弱转强
        if weak_to_strong_analysis:
            context_parts.append(f"\n【弱转强形态】")
            context_parts.append(f"弱转强: {'是' if weak_to_strong_analysis.get('weak_to_strong', False) else '否'}")
            context_parts.append(f"描述: {weak_to_strong_analysis.get('weak_to_strong_desc', '无')}")
        
        # 分时承接
        if intraday_support_analysis:
            context_parts.append(f"\n【分时承接】")
            context_parts.append(f"承接力度: {intraday_support_analysis.get('intraday_support_desc', '未知')}")
        
        # 技术指标
        context_parts.append(f"\n【技术指标】")
        rsi = technical_data.get('rsi', {})
        if rsi:
            context_parts.append(f"RSI: {rsi.get('RSI', 'N/A')}")
        
        macd = technical_data.get('macd', {})
        if macd:
            context_parts.append(f"MACD: {macd.get('Trend', 'N/A')}")
        
        money_flow = technical_data.get('money_flow', {})
        if money_flow:
            context_parts.append(f"资金流向: {money_flow.get('资金流向', 'N/A')}")
        
        return '\n'.join(context_parts)
    
    def _build_dragon_prompt(self, context: str) -> str:
        """构建龙头战法提示词（V3.0 暴力版）"""
        # 提取赛道信息（避免在 f-string 中使用反斜杠）
        sector = context.split('赛道: ')[1].split('\n')[0] if '赛道:' in context else '未知'
        newline = '\n'

        prompt = f"""【角色定义】
你不是传统的价值投资者，也不是看教科书的技术分析师。
你是A股顶级游资操盘手。你的唯一目标是：捕捉市场最强龙头的加速段。
你的信条："龙头多一条命"、"强者恒强"、"分歧是买点，一致是卖点"。

【核心禁令】
1. 禁止建议"等待回调"：龙头启动时不会回调，犹豫就是踏空。
2. 禁止使用 KDJ、MACD 金叉作为买入依据：这些指标太慢，等你看到金叉，车门早焊死了。
3. 禁止看市盈率 (PE/PB)：短线博弈只看情绪和资金，基本面只看有没有雷。

【分析流程】
第一步：身份核查 (Code Check)
- 代码前缀：{sector}
- 是否为 ST：检查代码中是否包含 ST

第二步：龙头辨识度
- 它是唯一的吗？（板块内唯一涨停/最高板）
- 它是最早的吗？（率先上板，带动板块）
- 它有伴吗？（板块内有3只以上涨停助攻）

第三步：资金微观结构
- 竞价爆量：9:25分成交量 / 昨天全天成交量 > 10%
- 弱转强：昨天炸板/大阴线，今天高开逾越压力位
- 分时强承接：股价在均线上方运行，下跌缩量，上涨放量

第四步：最终决策矩阵
根据以下维度评分并输出决策：
- 龙头地位（40%）
- 竞价强度（20%）
- 弱转强形态（20%）
- 分时承接（20%）

【当前数据】
{context}

【输出格式】
请务必只返回标准的 JSON 格式，不要包含 markdown 标记或其他文字：
{{
    "score": [0-100的评分, 龙头股必须给85分以上],
    "role": "龙头" | "中军" | "跟风" | "杂毛",
    "signal": "BUY_AGGRESSIVE" (猛干) | "BUY_DIP" (低吸) | "WAIT" (观望) | "SELL" (跑),
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "reason": "简短理由，例如：'AI眼镜核心龙头，20cm突破平台，竞价爆量弱转强，直接扫板'",
    "stop_loss_price": [具体止损价]
}}

注意：
1. 只输出 JSON，不要有任何其他文字
2. score: 0-100，龙头股必须给85分以上
3. signal: BUY_AGGRESSIVE(猛干), BUY_DIP(低吸), WAIT(观望), SELL(跑)
4. role: 龙头/中军/跟风/杂毛
5. confidence: HIGH/MEDIUM/LOW
6. stop_loss_price: 具体止损价
"""
        return prompt
    
    def _parse_dragon_response(self, response_text: str) -> Dict[str, Any]:
        """解析龙头战法 LLM 响应"""
        import re
        try:
            cleaned = re.sub(r'```json\s*|\s*```', '', response_text).strip()
            result = json.loads(cleaned)
            
            # 验证必需字段
            required_fields = ['score', 'role', 'signal', 'confidence', 'reason', 'stop_loss_price']
            for field in required_fields:
                if field not in result:
                    logger.warning(f"缺少必需字段: {field}")
                    result[field] = self._get_dragon_default_value(field)
            
            # 验证数据类型
            if not isinstance(result['score'], (int, float)):
                result['score'] = 50
            if result['role'] not in ['龙头', '中军', '跟风', '杂毛']:
                result['role'] = '跟风'
            if result['signal'] not in ['BUY_AGGRESSIVE', 'BUY_DIP', 'WAIT', 'SELL']:
                result['signal'] = 'WAIT'
            if result['confidence'] not in ['HIGH', 'MEDIUM', 'LOW']:
                result['confidence'] = 'MEDIUM'
            
            return result
            
        except Exception as e:
            logger.error(f"JSON 解析失败: {e}")
            return {
                "score": 50,
                "role": "跟风",
                "signal": "WAIT",
                "confidence": "MEDIUM",
                "reason": "解析失败",
                "stop_loss_price": 0
            }
    
    def _get_dragon_default_value(self, field: str) -> Any:
        """获取龙头战法字段的默认值"""
        defaults = {
            'score': 50,
            'role': '跟风',
            'signal': 'WAIT',
            'confidence': 'MEDIUM',
            'reason': '数据不足',
            'stop_loss_price': 0
        }
        return defaults.get(field, None)
    
    def _fallback_dragon_analysis(self,
                                   symbol: str,
                                   price_data: Dict[str, Any],
                                   technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """降级龙头战法分析"""
        # 简单规则
        change = price_data.get('change_percent', 0)
        
        if change >= 9.9:
            return {
                'score': 85,
                'role': '龙头',
                'signal': 'BUY_AGGRESSIVE',
                'confidence': 'HIGH',
                'reason': '涨停，疑似龙头',
                'stop_loss_price': price_data.get('current_price', 0) * 0.95
            }
        elif change >= 5:
            return {
                'score': 70,
                'role': '中军',
                'signal': 'BUY',
                'confidence': 'MEDIUM',
                'reason': '大涨，中军标的',
                'stop_loss_price': price_data.get('current_price', 0) * 0.95
            }
        else:
            return {
                'score': 50,
                'role': '跟风',
                'signal': 'WAIT',
                'confidence': 'LOW',
                'reason': '涨幅不够，观望',
                'stop_loss_price': price_data.get('current_price', 0) * 0.95
            }


# 使用示例
if __name__ == "__main__":
    # 使用 LLM 代理（需要配置 API Key）
    # ai_agent = RealAIAgent(api_key="your-api-key", provider="openai", model="gpt-4")

    # 使用规则代理（无需 API）
    rule_agent = RuleBasedAgent()

    # 模拟数据
    price_data = {
        'current_price': 10.50,
        'change_percent': 3.2,
        'volume': 5000000
    }

    technical_data = {
        'rsi': {'RSI': 65},
        'macd': {'Trend': '多头', 'Histogram': 0.05},
        'bollinger': {'上轨': 10.80, '下轨': 9.50, 'Trend': '上行'},
        'money_flow': {'资金流向': '流入', '主力净流入': 1000000},
        'kdj': {'K': 60, 'D': 55, 'J': 70}
    }

    # 分析
    report = rule_agent.analyze_stock("000001", price_data, technical_data)
    print(report)


# 向后兼容：DeepSeekAgent 作为 RuleBasedAgent 的别名
# 保持与旧代码的兼容性
DeepSeekAgent = RuleBasedAgent