"""开发单元模型 —— 阶段 4 运行时模型。

定义 DevUnit、UnitState、ReviewResult、UnitSummary。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ReviewResult(BaseModel):
    """单元审查结果。"""

    passed: bool
    feedback: str = ""
    issues: list[dict[str, Any]] = Field(default_factory=list)
    reviewer: str = ""

    @field_validator("feedback", "reviewer", mode="before")
    @classmethod
    def _coerce_to_str(cls, v: Any) -> str:
        """将 None 转为空字符串。"""
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)


class ArchitectNote(BaseModel):
    """架构师修改审核记录。"""

    unit_id: str
    reviewer_feedback: str  # 审查方原始反馈
    architect_decision: str  # 架构师的审核决定
    modified_instruction: str = ""  # 返回给开发员工的修改指令

    @field_validator("reviewer_feedback", "architect_decision", "modified_instruction", mode="before")
    @classmethod
    def _coerce_to_str(cls, v: Any) -> str:
        """将 None 转为空字符串。"""
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)


class UnitSummary(BaseModel):
    """单元开发的结构化总结。"""

    unit_id: str
    developer: str
    what_was_done: str  # 实现了什么
    constraints_satisfied: str  # 如何满足约束
    issues_encountered: str = ""  # 遇到的问题及解决方式
    final_result: str  # passed | failed | escalated
    total_redo_count: int = 0

    @field_validator("what_was_done", "constraints_satisfied", "issues_encountered", "final_result", mode="before")
    @classmethod
    def _coerce_to_str(cls, v: Any) -> str:
        """将 None 转为空字符串。"""
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)


class DevUnit(BaseModel):
    """运行时开发单元 —— 围绕一个 BlueprintUnit 的 Phase 4 包装。"""

    unit_id: str
    status: str = "pending"  # pending | claimed | in_progress | review | passed | failed
    developer: str = ""
    submitted_code: str = ""
    execution_summary: str = ""
    review_results: list[ReviewResult] = Field(default_factory=list)
    architect_notes: list[ArchitectNote] = Field(default_factory=list)
    redo_count: int = 0
    summary: Optional[UnitSummary] = None
