"""需求文档模型 —— 阶段 1 产物。

定义 RequirementDoc 及其子结构：Feature, UserScenario, AcceptanceCriterion, NonFunctionalConstraints。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class AcceptanceCriterion(BaseModel):
    """验收标准 —— 可独立测试的通过条件。"""

    id: str
    description: str
    testable_condition: str  # 客观可验证的条件描述
    feature_id: str  # 关联的功能点 ID


class UserScenario(BaseModel):
    """用户场景。"""

    id: str
    persona: str  # 用户画像
    goal: str  # 用户目标
    steps: list[str] = Field(default_factory=list)  # 操作步骤
    expected_outcome: str  # 预期结果


class Feature(BaseModel):
    """功能点定义。"""

    id: str
    title: str
    description: str
    priority: str = "medium"  # high | medium | low
    acceptance_criteria_ids: list[str] = Field(default_factory=list)
    business_value: str = ""  # 业务价值说明


class NonFunctionalConstraints(BaseModel):
    """非功能约束。

    LLM 可能输出嵌套 dict（如 performance: {frame_rate: ..., cpu_usage: ...}），
    通过 field_validator 自动扁平化为多行字符串。
    """

    performance: str = ""
    security: str = ""
    scalability: str = ""
    availability: str = ""
    compliance: str = ""

    @field_validator("performance", "security", "scalability", "availability", "compliance", mode="before")
    @classmethod
    def _flatten_dict_to_str(cls, v: Any) -> str:
        """将 dict 值扁平化为 \"key: value\" 格式的字符串。"""
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return "\n".join(f"{k}: {v}" for k, v in v.items())
        return str(v)


class RequirementDoc(BaseModel):
    """需求文档 —— 阶段 1 的最终产物。"""

    title: str
    description: str = ""
    features: list[Feature] = Field(default_factory=list)
    user_scenarios: list[UserScenario] = Field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    non_functional: NonFunctionalConstraints = Field(default_factory=NonFunctionalConstraints)
    baseline_confirmed: bool = False  # 人工确认后设为 True

    def to_summary(self) -> str:
        """生成需求文档的文本摘要。"""
        lines = [
            f"# 需求文档: {self.title}",
            f"",
            f"## 概述",
            f"{self.description}",
            f"",
            f"## 功能点 ({len(self.features)} 个)",
        ]
        for f in self.features:
            lines.append(f"- [{f.priority.upper()}] {f.id}: {f.title}")
            lines.append(f"  {f.description}")
            if f.business_value:
                lines.append(f"  业务价值: {f.business_value}")

        lines.append(f"")
        lines.append(f"## 用户场景 ({len(self.user_scenarios)} 个)")
        for s in self.user_scenarios:
            lines.append(f"- {s.id}: {s.persona} → {s.goal}")
            for step in s.steps:
                lines.append(f"  {step}")
            lines.append(f"  预期结果: {s.expected_outcome}")

        lines.append(f"")
        lines.append(f"## 验收标准 ({len(self.acceptance_criteria)} 个)")
        for ac in self.acceptance_criteria:
            lines.append(f"- {ac.id}: {ac.description}")
            lines.append(f"  可测试条件: {ac.testable_condition}")

        lines.append(f"")
        lines.append(f"## 非功能约束")
        lines.append(f"- 性能: {self.non_functional.performance or '未指定'}")
        lines.append(f"- 安全: {self.non_functional.security or '未指定'}")
        lines.append(f"- 可扩展性: {self.non_functional.scalability or '未指定'}")
        lines.append(f"- 可用性: {self.non_functional.availability or '未指定'}")
        lines.append(f"- 合规: {self.non_functional.compliance or '未指定'}")

        return "\n".join(lines)
