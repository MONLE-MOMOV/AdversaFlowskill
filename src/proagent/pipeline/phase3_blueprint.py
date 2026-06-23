"""阶段 3: 蓝图设计。

AI架构师（设计方） ↔ AI架构审核（验证方）
输入：冻结的项目计划
输出：DAG 形式的蓝图（唯一真理源）
"""

from __future__ import annotations

import json
from typing import Any

from proagent.pipeline.base import BasePhase
from proagent.models.state import PipelineState


class Phase3Blueprint(BasePhase):
    """阶段 3: 蓝图设计。"""

    proposer_role_key = "architect"
    challenger_role_key = "architecture_reviewer"

    @property
    def review_criteria(self) -> list[str]:
        return [
            "需求覆盖：是否完全覆盖了需求基线的所有功能？每个需求是否有对应的单元？",
            "粒度合理性：单元拆分是否过大（难以审查）或过小（碎片化）？",
            "接口兼容性：上下游接口是否匹配？数据格式是否一致？",
            "非功能约束：性能、安全、资源约束是否在每个单元中可验证？",
            "DAG 正确性：依赖关系是否合理？是否存在循环依赖？接口方向是否正确？",
        ]

    def build_context(self, state: PipelineState) -> dict[str, Any]:
        phase1 = state.phases["1"]
        phase2 = state.phases["2"]
        return {
            "需求基线": phase1.artifacts.get("requirement_doc", {}),
            "项目计划": phase2.artifacts.get("project_plan", {}),
        }

    def task_instruction(self, state: PipelineState) -> str:
        phase1 = state.phases["1"]
        phase2 = state.phases["2"]

        return f"""基于以下项目计划，将实现方式拆解为一系列紧密关联的小单元，构成有向无环图：

需求基线：
{json.dumps(phase1.artifacts.get("requirement_doc", {}), ensure_ascii=False, indent=2)}

项目计划：
{json.dumps(phase2.artifacts.get("project_plan", {}), ensure_ascii=False, indent=2)}

每个小单元必须包含：
- id: 唯一标识
- name: 名称
- description: 描述
- input_spec: 输入定义（接口契约、数据格式）
- output_spec: 输出定义（接口契约、数据格式）
- implementation_approach: 实现方式与核心算法/技术选型
- constraints: {{performance, security, resource_limits}}
- dependencies: 依赖的单元 ID 列表
- priority: 开发优先级（数字越小越优先）
- phase_id: 所属环节

要求：
1. 完全覆盖需求基线的所有功能点
2. 单元粒度合理
3. 接口兼容且无循环依赖

请输出包含以下内容的 JSON：
- title: 蓝图标题
- units: 单元列表（如上定义的所有字段）
- dag_description: DAG 结构描述（文本说明各层依赖关系）"""

    def on_convergence(
        self, state: PipelineState, debate_result: dict[str, Any]
    ) -> None:
        """蓝图入库 —— 成为唯一真理源。"""
        from proagent.models.blueprint import Blueprint, BlueprintUnit

        artifact = debate_result["final_artifact"]
        phase_state = state.get_current_phase()
        try:
            units_data = artifact.get("units", [])
            units = [BlueprintUnit(**u) for u in units_data]
            blueprint = Blueprint.from_units(
                title=artifact.get("title", "未命名蓝图"),
                units=units,
            )

            # 验证 DAG
            errors = blueprint.dag.validate_dag()
            if errors:
                phase_state.artifacts["dag_errors"] = errors

            phase_state.artifacts["blueprint"] = blueprint.model_dump()
            phase_state.artifacts["blueprint_approved"] = True

            # 初始化所有单元的 UnitState
            for unit in units:
                from proagent.models.state import UnitState
                phase_state.units[unit.id] = UnitState(
                    unit_id=unit.id,
                    status="pending",
                )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("蓝图解析失败: %s，保留原始数据", e)
            # 保留原始 artifact 作为后备
            phase_state.artifacts["blueprint"] = artifact
            phase_state.artifacts["blueprint_approved"] = True
