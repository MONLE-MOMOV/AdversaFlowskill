"""阶段 2: 项目规划。

AI项目经理（规划方） ↔ AI项目审核（挑战方）
输入：锁定的需求基线
输出：冻结的项目计划
"""

from __future__ import annotations

import json
from typing import Any

from proagent.pipeline.base import BasePhase
from proagent.models.state import PipelineState


class Phase2Planning(BasePhase):
    """阶段 2: 项目规划。"""

    proposer_role_key = "project_manager"
    challenger_role_key = "project_reviewer"

    @property
    def review_criteria(self) -> list[str]:
        return [
            "可行性：技术选型是否合理？是否考虑了替代方案的风险？",
            "资源冲突：是否存在资源竞争或瓶颈？AI 员工配置是否合理？",
            "依赖风险：关键路径上的依赖是否可控？是否有单点故障？",
            "环节完整性：是否遗漏了必要的环节？各环节边界是否清晰？",
            "风险评估：是否充分识别并缓解了主要风险？",
        ]

    def build_context(self, state: PipelineState) -> dict[str, Any]:
        phase1 = state.phases["1"]
        return {
            "需求基线": phase1.artifacts.get("requirement_doc", {}),
            "原始需求": state.original_requirement,
        }

    def task_instruction(self, state: PipelineState) -> str:
        phase1 = state.phases["1"]
        req_doc = phase1.artifacts.get("requirement_doc", {})

        return f"""基于以下已锁定的需求基线，制定可执行的项目计划：

需求基线：
{json.dumps(req_doc, ensure_ascii=False, indent=2)}

请输出包含以下内容的 JSON：
- title: 项目名称
- implementation_approach: 总体实现方式（架构思路、核心设计决策）
- tech_stack: {{
    languages: [...], frameworks: [...], databases: [...],
    infrastructure: [...], tools: [...]
  }}
- phases: 项目环节列表 [{{
    id, name, description, tasks: [...], order
  }}]
- tasks: 任务列表 [{{
    id, title, phase_id, priority(high/medium/low),
    dependencies: [...], estimated_effort, assigned_role
  }}]
- role_assignments: AI 员工配置 [{{
    role_name, tasks: [...], description
  }}]
- risk_register: 风险登记册 [{{
    id, description, severity(high/medium/low),
    probability(high/medium/low), mitigation, contingency
  }}]"""

    def on_convergence(
        self, state: PipelineState, debate_result: dict[str, Any]
    ) -> None:
        """计划冻结。"""
        from proagent.models.plan import ProjectPlan

        artifact = debate_result["final_artifact"]
        phase_state = state.get_current_phase()
        try:
            plan = ProjectPlan(**artifact)
            phase_state.artifacts["project_plan"] = plan.model_dump()
            phase_state.artifacts["plan_frozen"] = True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("ProjectPlan 解析失败，使用原始数据: %s", e)
            phase_state.artifacts["project_plan"] = artifact
            phase_state.artifacts["plan_frozen"] = True
