"""里程碑报告模型 —— 阶段 7 产物。

定义 MilestoneReport、Deviation、RiskAlert。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


def _str_or_empty(v: Any) -> str:
    """将 None 或非字符串值安全转为字符串。"""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


class Deviation(BaseModel):
    """与蓝图/需求基线的偏差。"""

    description: str = ""
    reference: str = ""  # 引用的蓝图单元或需求 ID
    severity: str = "minor"  # major | minor
    reason: str = ""
    resolution: str = ""  # 处理方案

    @field_validator("description", "reference", "severity", "reason", "resolution", mode="before")
    @classmethod
    def _coerce_strs(cls, v: Any) -> str:
        return _str_or_empty(v)


class RiskAlert(BaseModel):
    """风险提示。"""

    category: str = ""  # 技术 | 进度 | 资源
    description: str = ""
    severity: str = "medium"  # high | medium | low
    recommendation: str = ""

    @field_validator("category", "description", "severity", "recommendation", mode="before")
    @classmethod
    def _coerce_strs(cls, v: Any) -> str:
        return _str_or_empty(v)


class MilestoneReport(BaseModel):
    """里程碑会议报告。

    触发时机：每个小单元完成、每个环节完成、项目终了。
    """

    trigger: str = ""  # unit_complete | phase_complete | project_end
    trigger_reference: str = ""  # 引用的单元 ID 或阶段编号
    completion_summary: str = ""  # 完成度总结
    deviation_analysis: list[Deviation] = Field(default_factory=list)  # 偏离分析
    risk_alerts: list[RiskAlert] = Field(default_factory=list)  # 风险提示
    go_no_go_recommendation: str = ""  # 是否继续推进的建议
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    human_decision: str = ""  # 人工最终裁决

    @field_validator("trigger", "trigger_reference", "completion_summary", "go_no_go_recommendation", "human_decision", mode="before")
    @classmethod
    def _coerce_strs(cls, v: Any) -> str:
        return _str_or_empty(v)
