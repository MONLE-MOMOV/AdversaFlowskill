"""提示词模板 —— 按阶段和角色构建上下文。

将当前流水线状态、已有产物和辩论历史拼接为完整的 LLM 输入。
"""

from __future__ import annotations

import json
from typing import Any


def build_proposer_prompt(
    role_system: str,
    task_instruction: str,
    context: dict[str, Any],
    output_format_hint: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    """构建提案方的完整提示词。

    Args:
        role_system: 角色系统提示词
        task_instruction: 具体任务指令
        context: 当前上下文（已有产物、需求基线等）
        output_format_hint: 输出格式提示

    Returns:
        (system_prompt, messages) 元组
    """
    system = f"""{role_system}

{output_format_hint}

当前上下文信息：
{json.dumps(context, ensure_ascii=False, indent=2)}"""

    messages = [
        {
            "role": "user",
            "content": f"请基于以上上下文，完成以下任务：\n\n{task_instruction}\n\n请输出结构化的 JSON 结果，放在 ```json 代码块中。",
        }
    ]

    return system, messages


def build_challenger_prompt(
    role_system: str,
    artifact: dict[str, Any],
    review_criteria: list[str],
    context: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    """构建挑战方的完整提示词。

    Args:
        role_system: 角色系统提示词
        artifact: 待审查的产物（提案方输出）
        review_criteria: 审查标准列表
        context: 补充上下文

    Returns:
        (system_prompt, messages) 元组
    """
    criteria_text = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(review_criteria))

    system = f"""{role_system}

审查标准：
{criteria_text}

补充上下文：
{json.dumps(context, ensure_ascii=False, indent=2)}"""

    messages = [
        {
            "role": "user",
            "content": f"""请审查以下产物，按照审查标准逐条检查。

产物内容：
{json.dumps(artifact, ensure_ascii=False, indent=2)}

请以 JSON 列表格式输出所有发现的问题，每个问题包含：
- item: 问题引用的具体条目
- severity: 严重程度（blocker/major/minor）
- rationale: 清晰的理由
- suggestion: 建议的改进方案

```json
[{{"item": "...", "severity": "blocker|major|minor", "rationale": "...", "suggestion": "..."}}]
```""",
        }
    ]

    return system, messages


def build_rebuttal_prompt(
    role_system: str,
    original_artifact: dict[str, Any],
    challenges: list[dict[str, Any]],
    task_instruction: str,
) -> tuple[str, list[dict[str, Any]]]:
    """构建提案方回应挑战的提示词。

    Args:
        role_system: 角色系统提示词
        original_artifact: 原始产物
        challenges: 挑战方提出的问题列表
        task_instruction: 任务说明

    Returns:
        (system_prompt, messages) 元组
    """
    challenges_text = json.dumps(challenges, ensure_ascii=False, indent=2)

    system = f"""{role_system}

你的工作受到了以下挑战，请逐条回应。对于每条挑战，你可以选择：
- accept: 接受建议并修改
- reject: 拒绝建议（需要给出充分理由）
- defer: 标记为待人工裁决

请同时输出修订后的完整产物。"""

    messages = [
        {
            "role": "user",
            "content": f"""原始产物：
{json.dumps(original_artifact, ensure_ascii=False, indent=2)}

挑战方意见：
{challenges_text}

{task_instruction}

请以 JSON 格式输出，包含：
- responses: 每条挑战的回应列表 [{{"challenge_index": 0, "action": "accept|reject|defer", "rationale": "..."}}]
- revised_artifact: 修订后的完整产物

```json
{{"responses": [...], "revised_artifact": {{...}}}}
```""",
        }
    ]

    return system, messages
