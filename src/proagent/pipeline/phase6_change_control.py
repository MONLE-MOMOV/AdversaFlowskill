"""阶段 6: 蓝图变更控制。

AI架构师（变更评估方） ↔ AI架构审核（变更阻力方）
评估变更影响，决定是否启动正式变更流程。
"""

from __future__ import annotations

import json
from typing import Any

from proagent.pipeline.base import BasePhase
from proagent.models.state import PipelineState


class Phase6ChangeControl(BasePhase):
    """阶段 6: 蓝图变更控制。"""

    proposer_role_key = "architect"
    challenger_role_key = "architecture_reviewer"

    @property
    def review_criteria(self) -> list[str]:
        return [
            "变更必要性：变更是必须的还是可选的？能否通过现有蓝图达成？",
            "影响范围：将影响哪些单元？影响是否可以局部化？",
            "可行性：新蓝图版本在技术和资源上是否可行？",
            "回归风险：变更是否引入新的风险？",
            "一致性：变更后的蓝图是否仍满足原始需求基线？",
        ]

    def build_context(self, state: PipelineState) -> dict[str, Any]:
        return {
            "当前蓝图": state.phases["3"].artifacts.get("blueprint", {}),
            "需求基线": state.phases["1"].artifacts.get("requirement_doc", {}),
            "已完成的单元": {
                uid: us.model_dump()
                for uid, us in state.phases["4"].units.items()
                if us.status == "passed"
            },
            "阶段5闭环报告": state.phases["5"].artifacts,
        }

    def task_instruction(self, state: PipelineState) -> str:
        phase5 = state.phases["5"]
        reports = phase5.milestone_reports

        return f"""基于阶段 5 的闭环报告，评估是否需要启动蓝图变更：

阶段 5 报告：
{json.dumps(reports, ensure_ascii=False, indent=2)}

请分析：
1. 是否需要启动正式变更？
2. 变更的影响范围有哪些？
3. 新蓝图的建议调整方案

输出 JSON：
{{
    "change_needed": true/false,
    "change_description": "...",
    "affected_units": [...],
    "proposed_blueprint_updates": {{...}},
    "rationale": "..."
}}"""

    def on_convergence(
        self, state: PipelineState, debate_result: dict[str, Any]
    ) -> None:
        """处理变更决策。"""
        artifact = debate_result["final_artifact"]
        phase_state = state.get_current_phase()

        if artifact.get("change_needed"):
            # 记录变更请求
            from proagent.models.change import ChangeRequest, ChangeImpact

            cr = ChangeRequest(
                id=f"cr_{state.project_id}_{state.current_phase}",
                source_phase="phase5",
                description=artifact.get("change_description", ""),
                rationale=artifact.get("rationale", ""),
                impact=ChangeImpact(
                    affected_units=artifact.get("affected_units", []),
                    blueprint_version=state.phases["3"]
                    .artifacts.get("blueprint", {})
                    .get("version", 1),
                    effort_estimate="待评估",
                ),
            )
            phase_state.change_requests.append(cr.model_dump())

            # 如果双方达成一致或僵局 → 触发变更委员会
            if debate_result["status"] in ("converged", "deadlocked"):
                logger = __import__("logging").getLogger(__name__)
                logger.info("触发变更委员会：全角色 AI + 人类联合评审")
                # 实际委员会逻辑需要结合人力输入
                phase_state.artifacts["change_committee_triggered"] = True
