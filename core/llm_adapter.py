"""
LLM API适配器 - 统一OpenAI和Anthropic Claude API接口
"""
import logging
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMAdapter(ABC):
    """LLM适配器基类"""

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Any:
        """统一的对话完成接口"""
        pass


class OpenAIAdapter(LLMAdapter):
    """OpenAI API适配器(也兼容OpenAI格式的第三方API)"""

    def __init__(self, api_key: str, base_url: str, model: str):
        import openai
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Any:
        """OpenAI格式的对话完成"""
        params = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            params["tools"] = tools
            params["tool_choice"] = kwargs.get("tool_choice", "auto")

        if "temperature" in kwargs:
            params["temperature"] = kwargs["temperature"]

        if "max_tokens" in kwargs:
            params["max_tokens"] = kwargs["max_tokens"]

        return self.client.chat.completions.create(**params)


class AnthropicAdapter(LLMAdapter):
    """Anthropic Claude官方API适配器"""

    def __init__(self, api_key: str, base_url: str, model: str):
        import anthropic
        # Anthropic官方API不需要base_url,如果提供了非官方URL则报错
        if base_url and base_url != "https://api.anthropic.com/v1":
            logger.warning(f"Anthropic官方API不使用自定义base_url: {base_url}")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Any:
        """Anthropic格式的对话完成,转换为OpenAI兼容的响应"""
        # 转换消息格式: OpenAI -> Anthropic
        anthropic_messages = self._convert_messages(messages)

        # 提取system消息
        system_message = None
        filtered_messages = []
        for msg in anthropic_messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                filtered_messages.append(msg)

        params = {
            "model": self.model,
            "messages": filtered_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        if system_message:
            params["system"] = system_message

        if tools:
            # 转换工具格式: OpenAI -> Anthropic
            params["tools"] = self._convert_tools(tools)

        if "temperature" in kwargs:
            params["temperature"] = kwargs["temperature"]

        # 调用Anthropic API
        response = self.client.messages.create(**params)

        # 转换响应格式: Anthropic -> OpenAI兼容
        return self._convert_response(response)

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """转换消息格式"""
        converted = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content", "")

            # Anthropic不支持system role在messages中,需要单独处理
            if role == "system":
                converted.append({"role": "system", "content": content})
            elif role == "tool":
                # 工具响应转换
                converted.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_call_id", ""),
                            "content": content
                        }
                    ]
                })
            elif role == "assistant" and msg.get("tool_calls"):
                # 助手的工具调用转换
                tool_uses = []
                for tool_call in msg["tool_calls"]:
                    import json
                    tool_uses.append({
                        "type": "tool_use",
                        "id": tool_call["id"],
                        "name": tool_call["function"]["name"],
                        "input": json.loads(tool_call["function"]["arguments"])
                    })

                content_blocks = []
                if content:
                    content_blocks.append({"type": "text", "text": content})
                content_blocks.extend(tool_uses)

                converted.append({
                    "role": "assistant",
                    "content": content_blocks
                })
            else:
                converted.append({"role": role, "content": content})

        return converted

    def _convert_tools(self, openai_tools: List[Dict]) -> List[Dict]:
        """转换工具格式: OpenAI -> Anthropic"""
        anthropic_tools = []
        for tool in openai_tools:
            if tool["type"] == "function":
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {})
                })
        return anthropic_tools

    def _convert_response(self, anthropic_response) -> Any:
        """转换响应格式: Anthropic -> OpenAI兼容"""
        # 创建OpenAI兼容的响应对象
        class OpenAICompatibleResponse:
            def __init__(self, anthropic_resp):
                self.choices = [self._create_choice(anthropic_resp)]
                self.id = anthropic_resp.id
                self.model = anthropic_resp.model
                self.usage = {
                    "prompt_tokens": anthropic_resp.usage.input_tokens,
                    "completion_tokens": anthropic_resp.usage.output_tokens,
                    "total_tokens": anthropic_resp.usage.input_tokens + anthropic_resp.usage.output_tokens
                }

            def _create_choice(self, anthropic_resp):
                """创建choice对象"""
                class Choice:
                    def __init__(self, resp):
                        self.message = self._create_message(resp)
                        self.finish_reason = resp.stop_reason

                    def _create_message(self, resp):
                        """创建message对象"""
                        class Message:
                            def __init__(self, r):
                                # 提取文本内容和工具调用
                                text_content = ""
                                tool_calls = []

                                for block in r.content:
                                    if block.type == "text":
                                        text_content += block.text
                                    elif block.type == "tool_use":
                                        import json
                                        tool_calls.append(type('ToolCall', (), {
                                            'id': block.id,
                                            'type': 'function',
                                            'function': type('Function', (), {
                                                'name': block.name,
                                                'arguments': json.dumps(block.input)
                                            })()
                                        })())

                                self.content = text_content if text_content else None
                                self.tool_calls = tool_calls if tool_calls else None
                                self.role = "assistant"

                        return Message(resp)

                return Choice(anthropic_resp)

        return OpenAICompatibleResponse(anthropic_response)


def create_llm_adapter(
    api_provider: str,
    api_key: str,
    base_url: str,
    model: str
) -> LLMAdapter:
    """
    创建LLM适配器工厂函数

    Args:
        api_provider: API提供商 ('openai', 'anthropic', 'claude-third-party', 'openrouter', 'custom')
        api_key: API密钥
        base_url: API基础URL
        model: 模型名称

    Returns:
        LLMAdapter实例
    """
    if api_provider == "anthropic":
        # Anthropic官方API
        return AnthropicAdapter(api_key, base_url, model)
    else:
        # OpenAI及所有OpenAI兼容的API (openai, claude-third-party, openrouter, custom)
        return OpenAIAdapter(api_key, base_url, model)
