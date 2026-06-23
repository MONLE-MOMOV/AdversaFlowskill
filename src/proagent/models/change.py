"""变更请求模型 —— 阶段 6 产物。

定义 ChangeRequest、ChangeImpact、ChangeDecision。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


def _str_or_empty(v: Any) -> str:
    """将 None 或非字符串值安全转为字符串。"""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


class ChangeImpact(BaseModel):
    """变更影响评估。"""

    affected_units: list[str] = Field(default_factory=list)  # 受影响的单元 ID
    blueprint_version: int = 1
    effort_estimate: str = ""  # 预估变更工作量
    risk_assessment: str = ""  # 风险评估

    @field_validator("effort_estimate", "risk_assessment", mode="before")
    @classmethod
    def _coerce_strs(cls, v: Any) -> str:
        return _str_or_empty(v)


class ChangeDecision(BaseModel):
    """变更决策。"""

    decision: str = "pending"  # pending | approved | rejected
    reason: str = ""
    approved_by: str = ""  # "human" | "committee" | "auto"

    @field_validator("decision", "reason", "approved_by", mode="before")
    @classmethod
    def _coerce_strs(cls, v: Any) -> str:
        return _str_or_empty(v)


class ChangeRequest(BaseModel):
    """变更请求 —— 阶段 6 的输入。"""

    id: str
    source_phase: str  # 发起变更的来源阶段
    description: str  # 变更描述
    rationale: str  # 变更理由
    impact: ChangeImpact = Field(default_factory=ChangeImpact)
    decision: ChangeDecision = Field(default_factory=ChangeDecision)
    new_blueprint_version: int = 0

    @field_validator("id", "source_phase", "description", "rationale", mode="before")
    @classmethod
    def _coerce_strs(cls, v: Any) -> str:
        return _str_or_empty(v)
