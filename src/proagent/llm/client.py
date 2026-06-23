"""LLM 客户端封装 —— 基于 Anthropic Python SDK。

提供统一的 send_message 接口，处理消息构建、模型调用和错误重试。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from proagent.config.settings import Settings, default_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Anthropic 客户端封装，提供单一 send_message 接口。"""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or default_settings
        self._client = anthropic.Anthropic()

    def send_message(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
    ) -> str:
        """发送消息并获取响应文本。

        Args:
            system_prompt: 系统提示词（设定角色和行为）
            messages: 消息列表，格式 [{"role": "user/assistant", "content": "..."}]

        Returns:
            模型响应中的纯文本内容
        """
        try:
            response = self._client.messages.create(
                model=self.settings.model,
                max_tokens=self.settings.max_tokens,
                system=system_prompt,
                thinking={"type": self.settings.thinking_type},
                output_config={"effort": self.settings.effort},
                messages=messages,
            )

            # 提取所有文本块
            text_parts: list[str] = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)

            return "\n".join(text_parts)

        except anthropic.BadRequestError as e:
            logger.error("请求参数错误: %s", e.message)
            raise
        except anthropic.RateLimitError as e:
            logger.warning("速率限制，等待后重试: %s", e.message)
            raise
        except anthropic.APIStatusError as e:
            logger.error("API 错误 (status=%s): %s", e.status_code, e.message)
            raise

    def send_with_json_output(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """发送消息并请求结构化 JSON 输出。

        Args:
            system_prompt: 系统提示词
            messages: 消息列表
            output_schema: JSON Schema 定义

        Returns:
            解析后的 JSON 对象
        """
        full_system = f"{system_prompt}\n\n你必须严格按照以下 JSON Schema 输出，放在 ```json 代码块中：\n{json.dumps(output_schema, ensure_ascii=False, indent=2)}"

        response_text = self.send_message(full_system, messages)

        # 尝试从响应中提取 JSON
        return self._extract_json(response_text)

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """从 LLM 响应中提取 JSON 块。"""
        # 尝试提取 ```json ... ``` 代码块
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            json_str = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            json_str = text[start:end].strip()
        else:
            # 尝试直接解析整个响应
            json_str = text.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("无法从响应中解析 JSON，返回原始文本")
            return {"raw_text": text}


# 便捷函数
def create_client(settings: Settings | None = None) -> LLMClient:
    """创建 LLM 客户端实例。"""
    return LLMClient(settings)
