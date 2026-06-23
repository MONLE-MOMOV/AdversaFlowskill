"""阶段 4: 单元开发与闭环审查。

AI员工（实现方） ↔ AI单元审查（检查方）
按蓝图优先级与依赖关系，逐个认领并开发小单元。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from proagent.config.roles import get_role
from proagent.human.interface import BaseHumanInterface
from proagent.llm.client import LLMClient
from proagent.llm.prompts import build_proposer_prompt, build_challenger_prompt
from proagent.models.blueprint import Blueprint, BlueprintUnit
from proagent.models.state import PipelineState, UnitState
from proagent.models.unit import ArchitectNote, ReviewResult, UnitSummary
from proagent.pipeline.base import BasePhase, PhaseOutcome

logger = logging.getLogger(__name__)


class Phase4Development(BasePhase):
    """阶段 4: 单元开发与闭环审查。

    此阶段不同步运行完整的对抗辩论，而是逐个单元进行开发-审查循环。
    """

    proposer_role_key = "developer"
    challenger_role_key = "unit_reviewer"

    def __init__(self, llm_client: LLMClient, human, max_rounds: int = 3):
        super().__init__(llm_client, human, max_rounds)
        self._max_redo = max_rounds

    @property
    def review_criteria(self) -> list[str]:
        return [
            "蓝图符合性：代码是否严格按照蓝图的输入/输出定义实现？",
            "约束满足：是否满足蓝图中定义的所有非功能约束？",
            "代码质量：代码是否清晰、正确、可维护？",
            "测试覆盖：自测是否充分？",
            "接口兼容：输入/输出是否与上下游一致？",
        ]

    def build_context(self, state: PipelineState) -> dict[str, Any]:
        phase3 = state.phases["3"]
        return {
            "蓝图": phase3.artifacts.get("blueprint", {}),
            "当前状态": f"已完成 {sum(1 for u in state.get_current_phase().units.values() if u.status == 'passed')} / {len(state.get_current_phase().units)} 个单元",
        }

    def task_instruction(self, state: PipelineState) -> str:
        return "按照蓝图优先级和依赖关系，逐个开发小单元。"

    def run(self, state: PipelineState) -> PhaseOutcome:
        """阶段 4 的主循环 —— 逐个处理单元。"""
        phase_state = state.get_current_phase()
        phase_state.status = "in_progress"
        phase3 = state.phases["3"]

        blueprint_data = phase3.artifacts.get("blueprint", {})
        units_data = blueprint_data.get("units", [])

        if not units_data:
            logger.warning("没有蓝图单元，跳过阶段 4")
            phase_state.status = "completed"
            return PhaseOutcome(
                success=True,
                phase_num=state.current_phase,
                message="阶段 4 跳过: 蓝图中没有可开发的单元",
                next_phase=True,
            )

        try:
            units = [BlueprintUnit(**u) for u in units_data]
        except Exception as e:
            logger.error("蓝图单元解析失败: %s", e)
            phase_state.status = "blocked"
            return PhaseOutcome(
                success=False,
                phase_num=state.current_phase,
                message=f"蓝图单元解析失败: {e}",
                next_phase=False,
                requires_human=True,
            )

        bp = Blueprint.from_units(
            title=blueprint_data.get("title", "未命名蓝图"),
            units=units,
        )

        order = bp.dag.topological_order()
        logger.info("开发顺序: %s", " → ".join(order))

        completed: set[str] = {
            uid for uid, us in phase_state.units.items()
            if us.status == "passed"
        }

        for unit_id in order:
            if unit_id in completed:
                continue

            unit = next(u for u in units if u.id == unit_id)
            deps = set(unit.dependencies)

            if not deps.issubset(completed):
                logger.info("跳过 %s: 依赖未满足 (%s)", unit_id, deps - completed)
                continue

            logger.info("开始开发单元: %s - %s", unit_id, unit.name)
            self._develop_unit(state, unit, bp)

            completed.add(unit_id)

            # 每个单元完成时触发里程碑
            self._trigger_milestone(state, unit_id, "unit_complete")

        # 检查是否有需要人工裁决的单元
        failed_units = [
            uid for uid, us in phase_state.units.items()
            if us.status == "failed"
        ]
        if failed_units:
            phase_state.status = "blocked"
            return PhaseOutcome(
                success=False,
                phase_num=state.current_phase,
                message=f"阶段 4 部分完成: {len(failed_units)} 个单元需要人工裁决",
                next_phase=False,
                requires_human=True,
            )

        # 人工确认
        confirmed = self.human.confirm(
            f"阶段 {state.current_phase} 完成。\n"
            f"已开发单元: {len(completed)}\n"
            f"通过: {len(completed) - len(failed_units)}\n\n"
            f"是否确认并继续下一阶段？"
        )

        if confirmed:
            phase_state.status = "completed"
            return PhaseOutcome(
                success=True,
                phase_num=state.current_phase,
                message=f"阶段 4 完成: {len(completed)} 个单元已开发",
                next_phase=True,
            )
        else:
            phase_state.status = "blocked"
            return PhaseOutcome(
                success=False,
                phase_num=state.current_phase,
                message="阶段 4 等待人工处理",
                next_phase=False,
                requires_human=True,
            )

    def _develop_unit(
        self,
        state: PipelineState,
        unit: BlueprintUnit,
        blueprint: Blueprint,
    ) -> None:
        """开发单个单元，含审查循环。"""
        phase_state = state.get_current_phase()
        unit_state = phase_state.units.get(unit.id, UnitState(unit_id=unit.id))

        developer_role = get_role("developer")
        reviewer_role = get_role("unit_reviewer")

        for redo in range(self._max_redo + 1):
            # ========== 开发（或重做） ==========
            unit_state.status = "in_progress"
            logger.info("开发单元 %s (第 %d 次)", unit.id, redo + 1)

            context = {
                "蓝图单元定义": unit.model_dump(),
                "蓝图 DAG": {
                    "拓扑排序": blueprint.dag.topological_order(),
                    "依赖": unit.dependencies,
                },
            }

            system, messages = build_proposer_prompt(
                role_system=developer_role.system_prompt,
                task_instruction=f"""请实现以下蓝图单元：

单元名称: {unit.name}
单元 ID: {unit.id}
输入定义: {unit.input_spec}
输出定义: {unit.output_spec}
实现方式: {unit.implementation_approach}
约束: 性能={unit.constraints.performance}, 安全={unit.constraints.security}, 资源={unit.constraints.resource_limits}

请输出：
1. 实际代码实现
2. 自测方式和结果
3. 执行小结（实现了什么、如何满足约束、遇到的问题及解决方式）

以 JSON 格式输出：
```json
{{
    "code": "...",
    "self_test": "...",
    "summary": {{
        "what_was_done": "...",
        "constraints_satisfied": "...",
        "issues_encountered": "..."
    }}
}}
```""",
                context=context,
            )

            dev_response = self.llm.send_message(system, messages)
            dev_data = self._extract_json(dev_response)

            unit_state.submitted_code = dev_data.get("code", "")
            unit_state.execution_summary = json.dumps(
                dev_data.get("summary", {}), ensure_ascii=False
            )

            # ========== 审查 ==========
            unit_state.status = "review"
            logger.info("审查单元 %s", unit.id)

            system, messages = build_challenger_prompt(
                role_system=reviewer_role.system_prompt,
                artifact={
                    "蓝图定义": unit.model_dump(),
                    "提交代码": unit_state.submitted_code,
                    "自测小结": unit_state.execution_summary,
                },
                review_criteria=self.review_criteria,
                context={},
            )

            review_response = self.llm.send_message(system, messages)
            review_data = self._extract_json(review_response)

            if isinstance(review_data, dict):
                review_data = [review_data]

            passed = all(
                r.get("passed", r.get("severity") != "blocker")
                for r in review_data
            )

            review_result = ReviewResult(
                passed=passed,
                feedback=json.dumps(review_data, ensure_ascii=False),
                reviewer="AI 单元审查",
            )
            unit_state.review_results.append(review_result.model_dump())

            if passed:
                unit_state.status = "passed"
                logger.info("✅ 单元 %s 审查通过", unit.id)
                # 记录结构总结
                summary = UnitSummary(
                    unit_id=unit.id,
                    developer="AI 开发员工",
                    what_was_done=dev_data.get("summary", {}).get("what_was_done", ""),
                    constraints_satisfied=dev_data.get("summary", {}).get(
                        "constraints_satisfied", ""
                    ),
                    issues_encountered=dev_data.get("summary", {}).get(
                        "issues_encountered", ""
                    ),
                    final_result="passed",
                    total_redo_count=redo,
                )
                unit_state.summary = summary.model_dump()
                phase_state.units[unit.id] = unit_state
                return

            # ========== 修改建议先经架构师审核 ==========
            logger.info("单元 %s 审查未通过，架构师审核修改建议", unit.id)

            architect_role = get_role("architect")
            system, messages = build_proposer_prompt(
                role_system=architect_role.system_prompt,
                task_instruction=f"""审查方对单元 {unit.id} 提出了以下修改建议：

{json.dumps(review_data, ensure_ascii=False, indent=2)}

蓝图原始定义：
{json.dumps(unit.model_dump(), ensure_ascii=False, indent=2)}

请审核这些修改建议是否与蓝图整体设计一致。输出：
- decision: "approved" | "modified"
- modified_instruction: 返回给开发员工的重做指令（若修改了审查建议）
- rationale: 你的决定理由""",
                context={"蓝图": blueprint.model_dump()},
            )

            arch_response = self.llm.send_message(system, messages)
            arch_data = self._extract_json(arch_response)

            arch_note = ArchitectNote(
                unit_id=unit.id,
                reviewer_feedback=json.dumps(review_data, ensure_ascii=False),
                architect_decision=arch_data.get("decision", "approved"),
                modified_instruction=arch_data.get("modified_instruction", ""),
            )
            unit_state.architect_notes.append(arch_note.model_dump())

            if redo >= self._max_redo:
                unit_state.status = "failed"
                logger.warning(
                    "🚫 单元 %s 超过 %d 次重做，升级人工裁决", unit.id, self._max_redo
                )

                summary = UnitSummary(
                    unit_id=unit.id,
                    developer="AI 开发员工",
                    what_was_done="",
                    constraints_satisfied="",
                    issues_encountered=f"超过 {self._max_redo} 次重做仍未通过",
                    final_result="escalated",
                    total_redo_count=redo,
                )
                unit_state.summary = summary.model_dump()

                # 升级人工裁决
                self.human.adjudicate([])
                break

            unit_state.redo_count = redo + 1
            unit_state.status = "pending"
            logger.info("重做单元 %s (第 %d 次重做)", unit.id, redo + 1)

        phase_state.units[unit.id] = unit_state

    def _trigger_milestone(
        self, state: PipelineState, unit_id: str, trigger: str
    ) -> None:
        """触发单元完成里程碑。"""
        from proagent.models.milestone import MilestoneReport

        report = MilestoneReport(
            trigger=trigger,
            trigger_reference=unit_id,
            completion_summary=f"单元 {unit_id} 已完成",
            go_no_go_recommendation="继续下一单元",
        )
        phase = state.get_current_phase()
        phase.milestone_reports.append(report.model_dump())

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """从 LLM 响应中提取 JSON。"""
        if "```json" in text:
            try:
                start = text.index("```json") + 7
                end = text.index("```", start)
                return json.loads(text[start:end].strip())
            except (ValueError, json.JSONDecodeError):
                pass
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return {"raw_text": text}
