"""阶段 7: 里程碑会议（强制收敛）。

触发：每个小单元完成、每个环节完成、项目终了
参与：全体 AI 角色 + 人类
输出：结构化报告（完成度、偏离分析、风险、推进建议）
"""

from __future__ import annotations

import json
import logging
from typing import Any

from proagent.llm.prompts import build_proposer_prompt
from proagent.models.state import PipelineState
from proagent.pipeline.base import BasePhase

logger = logging.getLogger(__name__)


class Phase7Milestone(BasePhase):
    """阶段 7: 里程碑会议。

    此阶段由 AI 项目经理和 AI 产品经理共同生成报告，
    然后交叉审查，最多 3 轮对抗。
    """

    proposer_role_key = "project_manager"
    challenger_role_key = "product_manager"

    @property
    def review_criteria(self) -> list[str]:
        return [
            "报告完整性：报告是否覆盖了所有关键维度？",
            "数据准确性：完成的单元/环节统计数据是否准确？",
            "偏差分析：是否充分识别了与基线的偏差？",
            "风险评估：风险是否充分且准确？缓解措施是否合理？",
            "决策建议：是否基于客观数据提出了合理的推进建议？",
        ]

    def build_context(self, state: PipelineState) -> dict[str, Any]:
        """收集所有阶段的完整上下文。"""
        return {
            "需求基线": state.phases["1"].artifacts.get("requirement_doc", {}),
            "项目计划": state.phases["2"].artifacts.get("project_plan", {}),
            "蓝图": state.phases["3"].artifacts.get("blueprint", {}),
            "开发状态": self._phase4_summary(state),
            "闭环报告": state.phases["5"].artifacts,
            "变更请求": state.phases["6"].artifacts,
        }

    def _phase4_summary(self, state: PipelineState) -> dict[str, Any]:
        """汇总阶段 4 状态。"""
        units = state.phases["4"].units
        total = len(units)
        passed = sum(1 for u in units.values() if u.status == "passed")
        failed = sum(1 for u in units.values() if u.status == "failed")
        in_progress = sum(
            1 for u in units.values() if u.status in ("in_progress", "review")
        )
        pending = sum(1 for u in units.values() if u.status == "pending")

        return {
            "total_units": total,
            "passed": passed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": pending,
            "completion_percentage": round(passed / total * 100, 1) if total > 0 else 0,
        }

    def task_instruction(self, state: PipelineState) -> str:
        summary = self._phase4_summary(state)

        return f"""请生成项目里程碑报告。

当前项目状态：
- 总单元数: {summary['total_units']}
- 已通过: {summary['passed']}
- 未通过: {summary['failed']}
- 进行中: {summary['in_progress']}
- 待开发: {summary['pending']}
- 完成率: {summary['completion_percentage']}%

请与 AI 产品经理协作，生成包含以下内容的结构化报告：

1. 完成度总结（已完成单元/环节 vs 计划）
2. 偏离分析（与蓝图、需求基线的差异）
3. 风险提示（技术、进度、资源）
4. 是否继续推进的建议

输出 JSON：
{{
    "completion_summary": "...",
    "deviation_analysis": [{{
        "description": "...",
        "reference": "...",
        "severity": "major|minor",
        "reason": "...",
        "resolution": "..."
    }}],
    "risk_alerts": [{{
        "category": "技术|进度|资源",
        "description": "...",
        "severity": "high|medium|low",
        "recommendation": "..."
    }}],
    "go_no_go_recommendation": "..."
}}"""

    def on_convergence(
        self, state: PipelineState, debate_result: dict[str, Any]
    ) -> None:
        """生成最终里程碑报告。"""
        from proagent.models.milestone import MilestoneReport, Deviation, RiskAlert

        artifact = debate_result["final_artifact"]

        report = MilestoneReport(
            trigger="project_end",
            trigger_reference="",
            completion_summary=artifact.get("completion_summary", ""),
            deviation_analysis=[
                Deviation(**d) for d in artifact.get("deviation_analysis", [])
            ],
            risk_alerts=[
                RiskAlert(**r) for r in artifact.get("risk_alerts", [])
            ],
            go_no_go_recommendation=artifact.get("go_no_go_recommendation", ""),
        )

        phase_state = state.get_current_phase()
        phase_state.milestone_reports.append(report.model_dump())
        phase_state.artifacts["final_report"] = report.model_dump()

        logger.info("里程碑报告已生成")
        logger.info("完成度: %s", report.completion_summary)
        logger.info("建议: %s", report.go_no_go_recommendation)
