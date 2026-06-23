"""阶段流水线基类 —— BasePhase。

定义所有 7 个阶段的统一接口和共享行为。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from proagent.config.roles import Role
from proagent.engine.debate import AdversarialDebateEngine
from proagent.human.interface import BaseHumanInterface
from proagent.llm.client import LLMClient
from proagent.models.state import (
    BLOCKED,
    IN_PROGRESS,
    DebateRoundRecord,
    PhaseState,
    PipelineState,
    UnresolvedItem,
)

logger = logging.getLogger(__name__)


class PhaseOutcome:
    """阶段执行结果。"""

    def __init__(
        self,
        success: bool,
        phase_num: int,
        message: str = "",
        next_phase: bool = True,
        requires_human: bool = False,
    ):
        self.success = success
        self.phase_num = phase_num
        self.message = message
        self.next_phase = next_phase
        self.requires_human = requires_human


class BasePhase(ABC):
    """阶段基类 —— 所有 7 个阶段继承此类。

    子类需要实现：
    - proposer_role_key: 提案方角色键
    - challenger_role_key: 挑战方角色键
    - review_criteria: 审查标准列表
    - task_instruction(): 任务指令
    - build_context(): 构建上下文
    - on_convergence(): 收敛后的处理
    """

    proposer_role_key: str = ""
    challenger_role_key: str = ""

    def __init__(
        self,
        llm_client: LLMClient,
        human: BaseHumanInterface,
        max_rounds: int = 3,
    ):
        self.llm = llm_client
        self.human = human
        self.max_rounds = max_rounds

    @property
    def proposer_role(self) -> Role:
        from proagent.config.roles import get_role
        return get_role(self.proposer_role_key)

    @property
    def challenger_role(self) -> Role:
        from proagent.config.roles import get_role
        return get_role(self.challenger_role_key)

    @property
    @abstractmethod
    def review_criteria(self) -> list[str]:
        """审查标准列表。"""
        ...

    @abstractmethod
    def build_context(self, state: PipelineState) -> dict[str, Any]:
        """构建当前阶段的上下文。"""
        ...

    @abstractmethod
    def task_instruction(self, state: PipelineState) -> str:
        """生成任务指令。"""
        ...

    def run(self, state: PipelineState) -> PhaseOutcome:
        """执行阶段。

        标准流程：
        1. 构建上下文和任务指令
        2. 启动对抗辩论引擎
        3. 处理辩论结果
        4. 如有未解决项，请求人工裁决
        5. 处理收敛后的逻辑
        """
        phase_state = state.get_current_phase()
        phase_state.status = IN_PROGRESS

        context = self.build_context(state)
        instruction = self.task_instruction(state)

        logger.info("开始阶段 %d: %s", state.current_phase, self.__class__.__name__)

        existing_artifact = phase_state.artifacts.get("data", None)

        engine = AdversarialDebateEngine(
            llm_client=self.llm,
            proposer_role=self.proposer_role,
            challenger_role=self.challenger_role,
            max_rounds=self.max_rounds,
        )

        result = engine.run(
            task_instruction=instruction,
            context=context,
            review_criteria=self.review_criteria,
            initial_artifact=existing_artifact,
        )

        # 记录辩论历史
        phase_state.artifacts["data"] = result["final_artifact"]
        phase_state.artifacts["debate_status"] = result["status"]

        for r in result["rounds"]:
            record = DebateRoundRecord(
                round_number=r["round_num"],
                proposer_output={},
                challenger_output=r["challenges"],
                proposer_response={"responses": r.get("responses", [])},
                converged=r["converged"],
            )
            phase_state.debate_history.append(record)

        # 处理未解决项
        unresolved_raw = result.get("unresolved_items", [])
        if unresolved_raw:
            logger.warning("有 %d 项未解决的争议", len(unresolved_raw))
            for item in unresolved_raw:
                ui = UnresolvedItem(
                    challenge=item.get("challenge", {}),
                    response=item.get("response", {}),
                    round_raised=len(result["rounds"]),
                    reason=item.get("reason", ""),
                )
                phase_state.unresolved_items.append(ui)

            human_decisions = self.human.adjudicate(phase_state.unresolved_items)
            for d in human_decisions:
                phase_state.human_decisions.append(d)

        # 子类自定义收敛处理
        self.on_convergence(state, result)

        # 人工确认
        confirmed = self.human.confirm(
            f"阶段 {state.current_phase} 完成。\n"
            f"状态: {result['status']}\n"
            f"总轮数: {result['total_rounds']}\n"
            f"未解决项: {len(unresolved_raw)}\n\n"
            f"是否确认并继续下一阶段？"
        )

        if confirmed:
            return PhaseOutcome(
                success=True,
                phase_num=state.current_phase,
                message=f"阶段 {state.current_phase} 完成",
                next_phase=True,
            )
        else:
            phase_state.status = BLOCKED
            return PhaseOutcome(
                success=False,
                phase_num=state.current_phase,
                message=f"阶段 {state.current_phase} 等待人工处理",
                next_phase=False,
                requires_human=True,
            )

    def on_convergence(
        self, state: PipelineState, debate_result: dict[str, Any]
    ) -> None:
        """辩论收敛后的回调 —— 子类可重写。"""
        pass
