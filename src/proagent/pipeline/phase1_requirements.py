"""阶段 1: 需求精炼。

AI产品经理（生成方） ↔ AI产品审核（质疑方）
输入：模糊需求
输出：结构化需求基线
"""

from __future__ import annotations

from typing import Any

from proagent.pipeline.base import BasePhase
from proagent.models.state import PipelineState


class Phase1Requirements(BasePhase):
    """阶段 1: 需求精炼。"""

    proposer_role_key = "product_manager"
    challenger_role_key = "product_reviewer"

    @property
    def review_criteria(self) -> list[str]:
        return [
            "完备性：是否覆盖了所有用户场景？边界情况和异常路径是否考虑？",
            "歧义性：每个需求是否只有一种理解方式？是否存在模糊表述？",
            "业务对齐：每个功能是否服务于明确的业务目标？",
            "可测试性：每个验收标准是否可以客观验证？",
            "一致性：功能之间是否存在冲突？描述是否前后一致？",
        ]

    def build_context(self, state: PipelineState) -> dict[str, Any]:
        return {
            "原始需求": state.original_requirement,
            "背景": "这是一个新项目的需求精炼阶段",
        }

    def task_instruction(self, state: PipelineState) -> str:
        return f"""请将以下模糊需求转化为结构化需求文档：

{state.original_requirement}

请输出包含以下内容的 JSON：
- title: 项目名称
- description: 概述
- features: 功能点列表 [{{
    id, title, description, priority(high/medium/low),
    acceptance_criteria_ids: [...], business_value
  }}]
- user_scenarios: 用户场景列表 [{{
    id, persona, goal, steps: [...], expected_outcome
  }}]
- acceptance_criteria: 验收标准列表 [{{
    id, description, testable_condition, feature_id
  }}]
- non_functional: {{performance, security, scalability, availability, compliance}}"""

    def on_convergence(
        self, state: PipelineState, debate_result: dict[str, Any]
    ) -> None:
        """需求基线确认。"""
        from proagent.models.requirements import RequirementDoc

        artifact = debate_result["final_artifact"]
        phase_state = state.get_current_phase()
        try:
            doc = RequirementDoc(**artifact)
            phase_state.artifacts["requirement_doc"] = doc.model_dump()
            phase_state.artifacts["baseline_confirmed"] = True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("RequirementDoc 解析失败，使用原始数据: %s", e)
            # 保留原始 artifact 作为后备
            phase_state.artifacts["requirement_doc"] = artifact
            phase_state.artifacts["baseline_confirmed"] = True
