"""主状态模型 —— PipelineState。

JSON 序列化的核心状态对象，追踪整个 7 阶段流水线的进度。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================
# 枚举
# ============================================================

class PhaseStatus(str):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


PENDING = "pending"
IN_PROGRESS = "in_progress"
COMPLETED = "completed"
BLOCKED = "blocked"


# ============================================================
# 辩论记录
# ============================================================

class DebateRoundRecord(BaseModel):
    """单轮对抗辩论记录。"""

    round_number: int
    proposer_output: dict[str, Any] = Field(default_factory=dict)
    challenger_output: list[dict[str, Any]] = Field(default_factory=list)
    proposer_response: dict[str, Any] = Field(default_factory=dict)
    unresolved: list[dict[str, Any]] = Field(default_factory=list)
    converged: bool = False


class UnresolvedItem(BaseModel):
    """未解决的争议项。"""

    challenge: dict[str, Any]
    response: dict[str, Any] = Field(default_factory=dict)
    round_raised: int
    reason: str = ""


class HumanDecision(BaseModel):
    """人工裁决记录。"""

    item_reference: str
    decision: str  # "approved" | "rejected" | "overridden"
    notes: str = ""
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================
# 单元状态（阶段 4）
# ============================================================

class UnitState(BaseModel):
    """开发单元运行时状态。"""

    unit_id: str
    status: str = PENDING  # pending | claimed | in_progress | review | passed | failed
    developer: str = ""
    submitted_code: str = ""
    execution_summary: str = ""
    review_results: list[dict[str, Any]] = Field(default_factory=list)
    architect_notes: list[dict[str, Any]] = Field(default_factory=list)
    redo_count: int = 0
    summary: Optional[dict[str, Any]] = None


# ============================================================
# 阶段状态
# ============================================================

class PhaseState(BaseModel):
    """单个阶段的状态。"""

    phase_number: int
    status: str = PENDING
    artifacts: dict[str, Any] = Field(default_factory=dict)
    debate_history: list[DebateRoundRecord] = Field(default_factory=list)
    current_round: int = 0
    unresolved_items: list[UnresolvedItem] = Field(default_factory=list)
    human_decisions: list[HumanDecision] = Field(default_factory=list)
    units: dict[str, UnitState] = Field(default_factory=dict)
    change_requests: list[dict[str, Any]] = Field(default_factory=list)
    milestone_reports: list[dict[str, Any]] = Field(default_factory=list)


# ============================================================
# 主状态
# ============================================================

class PipelineState(BaseModel):
    """全局流水线状态 —— 唯一真理源。"""

    schema_version: int = 1
    project_id: str = Field(default_factory=lambda: f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_phase: int = 1
    original_requirement: str = ""
    phases: dict[str, PhaseState] = Field(default_factory=dict)

    @classmethod
    def create(cls, requirement: str) -> "PipelineState":
        """创建新的流水线状态。"""
        state = cls(original_requirement=requirement)
        # 初始化所有 7 个阶段
        for i in range(1, 8):
            state.phases[str(i)] = PhaseState(
                phase_number=i,
                status=PENDING if i > 1 else IN_PROGRESS,
            )
        # 阶段 1 标记为进行中
        state.phases["1"].status = IN_PROGRESS
        return state

    def get_current_phase(self) -> PhaseState:
        """获取当前阶段的 PhaseState。"""
        return self.phases[str(self.current_phase)]

    def advance_phase(self) -> Optional[PhaseState]:
        """完成当前阶段，进入下一阶段。

        Returns:
            下一阶段的 PhaseState，如果没有下一阶段则返回 None
        """
        current = self.get_current_phase()
        current.status = COMPLETED

        if self.current_phase >= 7:
            return None

        self.current_phase += 1
        next_phase = self.get_current_phase()
        next_phase.status = IN_PROGRESS
        return next_phase

    def add_debate_round(self, phase_num: int, record: DebateRoundRecord) -> None:
        """添加辩论记录到指定阶段。"""
        phase = self.phases[str(phase_num)]
        phase.debate_history.append(record)
        phase.current_round = record.round_number
