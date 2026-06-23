"""阶段 5: 环节与需求闭环。

AI项目经理（完整性审核） ↔ AI产品经理（需求复核方）
检查环节是否完整、是否真正满足基线需求。
"""

from __future__ import annotations

import json
from typing import Any

from proagent.pipeline.base import BasePhase
from proagent.models.state import PipelineState


class Phase5Closure(BasePhase):
    """阶段 5: 环节与需求闭环。"""

    proposer_role_key = "project_manager"
    challenger_role_key = "product_manager"

    @property
    def review_criteria(self) -> list[str]:
        return [
            "单元完整性：该环节内所有单元是否均已达标？",
            "需求满足度：该环节是否真正满足了基线需求？",
            "遗漏检测：是否存在需求基线中定义但未实现的功能？",
            "偏差分析：实际实现与蓝图是否存在偏差？是否可接受？",
            "集成正确性：各单元集成后是否工作正常？",
        ]

    def build_context(self, state: PipelineState) -> dict[str, Any]:
        phase1 = state.phases["1"]
        phase4 = state.phases["4"]
        return {
            "需求基线": phase1.artifacts.get("requirement_doc", {}),
            "蓝图": state.phases["3"].artifacts.get("blueprint", {}),
            "已完成的单元": {
                uid: us.model_dump()
                for uid, us in phase4.units.items()
                if us.status == "passed"
            },
            "未通过的单元": {
                uid: us.model_dump()
                for uid, us in phase4.units.items()
                if us.status == "failed"
            },
        }

    def task_instruction(self, state: PipelineState) -> str:
        phase4 = state.phases["4"]
        total = len(phase4.units)
        passed = sum(1 for u in phase4.units.values() if u.status == "passed")

        return f"""请从完整性角度审核当前环节。

开发进度：{passed}/{total} 个单元已通过
{'尚有 ' + str(total - passed) + ' 个单元未通过' if total > passed else '所有单元均已通过'}

请评估：
1. 当前环节的所有单元是否均已达标？
2. 环节整体是否完整？
3. 是否满足基线需求？

输出 JSON：
{{
    "phase_complete": true/false,
    "requirements_met": [...],
    "gaps": [...],
    "overall_assessment": "..."
}}"""

    def on_convergence(
        self, state: PipelineState, debate_result: dict[str, Any]
    ) -> None:
        """生成闭环报告，征询人工是否有追加需求。"""
        from proagent.models.milestone import MilestoneReport, Deviation, RiskAlert

        artifact = debate_result["final_artifact"]
        phase_state = state.get_current_phase()

        report = MilestoneReport(
            trigger="phase_complete",
            trigger_reference=str(state.current_phase),
            completion_summary=artifact.get("overall_assessment", ""),
            deviation_analysis=[
                Deviation(description=g, reference="", severity="minor")
                for g in artifact.get("gaps", [])
            ],
            go_no_go_recommendation="继续" if artifact.get("phase_complete") else "需补充",
        )
        phase_state.milestone_reports.append(report.model_dump())
