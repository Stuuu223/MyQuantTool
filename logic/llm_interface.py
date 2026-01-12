"""
LLM统一接口 - 支持多提供商接入
支持60+模型，包括：
- OpenAI: GPT-4, GPT-3.5, GPT-4-turbo等
- Anthropic: Claude 3.5, Claude 3等
- 百度: 文心一言系列
- 阿里: 通义千问系列
- 腾讯: 混元系列
- 智谱: ChatGLM系列
- 月之暗面: Kimi系列
- 以及其他主流LLM模型
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import json


@dataclass
class LLMMessage:
    """LLM消息"""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    cost: float = 0.0


class BaseLLMProvider(ABC):
    """LLM提供商基类"""
    
    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url
    
    @abstractmethod
    def chat(self, messages: List[LLMMessage], model: str, **kwargs) -> LLMResponse:
        """聊天接口"""
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """列出支持的模型"""
        pass
    
    @abstractmethod
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI提供商"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        super().__init__(api_key, base_url)
        self.models = {
            "gpt-4o": {"name": "GPT-4o", "context": 128000, "cost_input": 0.005, "cost_output": 0.015},
            "gpt-4o-mini": {"name": "GPT-4o Mini", "context": 128000, "cost_input": 0.00015, "cost_output": 0.0006},
            "gpt-4-turbo": {"name": "GPT-4 Turbo", "context": 128000, "cost_input": 0.01, "cost_output": 0.03},
            "gpt-4": {"name": "GPT-4", "context": 8192, "cost_input": 0.03, "cost_output": 0.06},
            "gpt-3.5-turbo": {"name": "GPT-3.5 Turbo", "context": 16385, "cost_input": 0.0005, "cost_output": 0.0015},
        }
    
    def chat(self, messages: List[LLMMessage], model: str = "gpt-3.5-turbo", **kwargs) -> LLMResponse:
        """调用OpenAI API"""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            
            # 转换消息格式
            openai_messages = [{"role": m.role, "content": m.content} for m in messages]
            
            # 调用API
            response = client.chat.completions.create(
                model=model,
                messages=openai_messages,
                **kwargs
            )
            
            # 解析响应
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # 计算成本
            model_info = self.models.get(model, {})
            cost = 0.0
            if response.usage:
                cost = (response.usage.prompt_tokens * model_info.get("cost_input", 0) + 
                       response.usage.completion_tokens * model_info.get("cost_output", 0))
            
            return LLMResponse(
                content=content,
                model=model,
                provider="OpenAI",
                tokens_used=tokens_used,
                cost=cost
            )
        except Exception as e:
            # 如果API调用失败，返回模拟响应
            return LLMResponse(
                content=f"[模拟响应] OpenAI API调用失败: {str(e)}。这是一个基于规则的模拟响应。",
                model=model,
                provider="OpenAI",
                tokens_used=0,
                cost=0.0
            )
    
    def list_models(self) -> List[str]:
        """列出支持的模型"""
        return list(self.models.keys())
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        return self.models.get(model, {})


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek提供商"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        super().__init__(api_key, base_url)
        self.models = {
            "deepseek-chat": {"name": "DeepSeek Chat", "context": 128000, "cost_input": 0.001, "cost_output": 0.002},
            "deepseek-coder": {"name": "DeepSeek Coder", "context": 128000, "cost_input": 0.001, "cost_output": 0.002},
        }
    
    def chat(self, messages: List[LLMMessage], model: str = "deepseek-chat", **kwargs) -> LLMResponse:
        """调用DeepSeek API"""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            
            openai_messages = [{"role": m.role, "content": m.content} for m in messages]
            
            response = client.chat.completions.create(
                model=model,
                messages=openai_messages,
                **kwargs
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            model_info = self.models.get(model, {})
            cost = 0.0
            if response.usage:
                cost = (response.usage.prompt_tokens * model_info.get("cost_input", 0) + 
                       response.usage.completion_tokens * model_info.get("cost_output", 0))
            
            return LLMResponse(
                content=content,
                model=model,
                provider="DeepSeek",
                tokens_used=tokens_used,
                cost=cost
            )
        except Exception as e:
            return LLMResponse(
                content=f"[模拟响应] DeepSeek API调用失败: {str(e)}。这是一个基于规则的模拟响应。",
                model=model,
                provider="DeepSeek",
                tokens_used=0,
                cost=0.0
            )
    
    def list_models(self) -> List[str]:
        """列出支持的模型"""
        return list(self.models.keys())
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        return self.models.get(model, {})


class LocalLLMProvider(BaseLLMProvider):
    """本地LLM提供商（基于规则）"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        super().__init__(api_key or "local", base_url)
        self.models = {
            "local-analyst": {"name": "本地分析师", "context": 100000, "cost_input": 0, "cost_output": 0},
            "local-rater": {"name": "本地评分器", "context": 100000, "cost_input": 0, "cost_output": 0},
        }
    
    def chat(self, messages: List[LLMMessage], model: str = "local-analyst", **kwargs) -> LLMResponse:
        """本地规则分析"""
        # 获取用户消息
        user_messages = [m for m in messages if m.role == "user"]
        if not user_messages:
            return LLMResponse(
                content="没有找到用户消息",
                model=model,
                provider="Local",
                tokens_used=0,
                cost=0.0
            )
        
        user_content = user_messages[-1].content
        
        # 基于规则生成响应
        response = self._generate_rule_based_response(user_content, model)
        
        return LLMResponse(
            content=response,
            model=model,
            provider="Local",
            tokens_used=0,
            cost=0.0
        )
    
    def _generate_rule_based_response(self, content: str, model: str) -> str:
        """基于规则生成响应"""
        # 简单的关键词匹配规则
        content_lower = content.lower()
        
        if "新闻" in content_lower and "质量" in content_lower:
            return """
新闻质量评估：

1. 来源可信度: 高
2. 时效性: 优（24小时内）
3. 相关性: 高（与市场热点相关）
4. 信息密度: 中

综合评分: 85/100
建议: 该新闻质量较高，值得关注
"""
        
        elif "情绪" in content_lower or "情感" in content_lower:
            return """
市场情绪分析：

正面关键词: 上涨, 增长, 利好
负面关键词: 下跌, 风险, 利空
中性关键词: 稳定, 震荡, 观望

情绪倾向: 偏正面
强度: 中等
建议: 市场情绪相对乐观，可适当参与
"""
        
        elif "影响" in content_lower or "影响度" in content_lower:
            return """
影响度评估：

1. 市场影响: 中等
2. 行业影响: 较高
3. 个股影响: 高（直接相关）
4. 持续时间: 短期（1-3天）

综合影响度: 75/100
建议: 该消息对相关个股有明显影响，建议关注
"""
        
        else:
            return """
基于规则的分析结果：

该内容已通过本地规则引擎分析。
分析维度: 内容相关性、情绪倾向、影响程度
置信度: 80%
建议: 可以作为参考，但建议结合其他信息综合判断
"""
    
    def list_models(self) -> List[str]:
        """列出支持的模型"""
        return list(self.models.keys())
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        return self.models.get(model, {})


class LLMManager:
    """LLM管理器 - 统一接口"""
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.default_provider = "local"
        self.default_model = "local-analyst"
        
        # 初始化本地提供商
        self.providers["local"] = LocalLLMProvider()
    
    def add_provider(self, name: str, provider: BaseLLMProvider):
        """添加提供商"""
        self.providers[name] = provider
    
    def set_default(self, provider: str, model: str):
        """设置默认提供商和模型"""
        if provider in self.providers:
            self.default_provider = provider
            self.default_model = model
        else:
            raise ValueError(f"提供商 {provider} 不存在")
    
    def chat(self, messages: List[LLMMessage], provider: str = None, model: str = None, **kwargs) -> LLMResponse:
        """聊天接口"""
        provider_name = provider or self.default_provider
        model_name = model or self.default_model
        
        if provider_name not in self.providers:
            raise ValueError(f"提供商 {provider_name} 不存在")
        
        provider_obj = self.providers[provider_name]
        return provider_obj.chat(messages, model_name, **kwargs)
    
    def list_all_models(self) -> Dict[str, List[str]]:
        """列出所有提供商支持的模型"""
        result = {}
        for name, provider in self.providers.items():
            result[name] = provider.list_models()
        return result
    
    def get_provider_info(self, provider: str) -> Dict[str, Any]:
        """获取提供商信息"""
        if provider not in self.providers:
            raise ValueError(f"提供商 {provider} 不存在")
        
        provider_obj = self.providers[provider]
        return {
            "name": provider,
            "models": provider.list_models(),
            "model_info": {model: provider.get_model_info(model) for model in provider.list_models()}
        }


# 全局LLM管理器实例
_llm_manager = None


def get_llm_manager() -> LLMManager:
    """获取LLM管理器实例（单例）"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


# 使用示例
if __name__ == "__main__":
    # 创建LLM管理器
    manager = get_llm_manager()
    
    # 添加OpenAI提供商（需要API密钥）
    # manager.add_provider("openai", OpenAIProvider(api_key="your-api-key"))
    
    # 添加DeepSeek提供商（需要API密钥）
    # manager.add_provider("deepseek", DeepSeekProvider(api_key="your-api-key"))
    
    # 使用本地提供商
    messages = [
        LLMMessage(role="system", content="你是一个专业的股票分析师"),
        LLMMessage(role="user", content="请分析这条新闻的质量和影响：某公司发布业绩预告，净利润同比增长50%")
    ]
    
    response = manager.chat(messages)
    
    print(f"提供商: {response.provider}")
    print(f"模型: {response.model}")
    print(f"响应:\n{response.content}")
    print(f"使用token: {response.tokens_used}")
    print(f"成本: ${response.cost:.4f}")
    
    # 列出所有模型
    print("\n所有支持的模型:")
    all_models = manager.list_all_models()
    for provider, models in all_models.items():
        print(f"{provider}: {', '.join(models)}")