"""流水线编排器 —— 串联 7 个阶段。

PhaseConductor 负责：
- 加载/创建 PipelineState
- 按顺序执行各阶段
- 持久化中间状态
- 支持 --resume、--jump-to、--status
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from proagent.config.settings import Settings, default_settings
from proagent.llm.client import LLMClient
from proagent.human.interface import BaseHumanInterface
from proagent.models.state import PipelineState, BLOCKED, COMPLETED, IN_PROGRESS
from proagent.persistence.store import StateStore
from proagent.pipeline.base import BasePhase, PhaseOutcome
from proagent.pipeline.phase1_requirements import Phase1Requirements
from proagent.pipeline.phase2_planning import Phase2Planning
from proagent.pipeline.phase3_blueprint import Phase3Blueprint
from proagent.pipeline.phase4_development import Phase4Development
from proagent.pipeline.phase5_closure import Phase5Closure
from proagent.pipeline.phase6_change_control import Phase6ChangeControl
from proagent.pipeline.phase7_milestone import Phase7Milestone

logger = logging.getLogger(__name__)


class PhaseConductor:
    """流水线编排器 —— 串联并推进 7 个阶段的执行。"""

    def __init__(
        self,
        store: StateStore,
        llm_client: LLMClient,
        human: BaseHumanInterface,
        settings: Settings | None = None,
    ):
        self.store = store
        self.llm = llm_client
        self.human = human
        self.settings = settings or default_settings

    # ------------------------------------------------------------------
    # 阶段工厂
    # ------------------------------------------------------------------

    def _create_phase(self, phase_num: int, state: PipelineState) -> Optional[BasePhase]:
        """根据阶段编号创建对应的阶段实例。"""
        kwargs = {
            "llm_client": self.llm,
            "human": self.human,
            "max_rounds": self.settings.max_debate_rounds,
        }

        phase_classes: dict[int, type[BasePhase]] = {
            1: Phase1Requirements,
            2: Phase2Planning,
            3: Phase3Blueprint,
            4: Phase4Development,
            5: Phase5Closure,
            6: Phase6ChangeControl,
            7: Phase7Milestone,
        }

        cls = phase_classes.get(phase_num)
        if cls is None:
            logger.error("未知阶段: %d", phase_num)
            return None

        return cls(**kwargs)

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def advance(self, state: PipelineState) -> PipelineState:
        """推进流水线一个阶段。"""
        phase_num = state.current_phase
        phase_instance = self._create_phase(phase_num, state)

        if phase_instance is None:
            return state

        logger.info("=" * 50)
        logger.info("执行阶段 %d/%d: %s", phase_num, 7, type(phase_instance).__name__)
        logger.info("=" * 50)

        try:
            outcome = phase_instance.run(state)

            if outcome.success and outcome.next_phase:
                state.advance_phase()
                logger.info("阶段 %d 完成，进入阶段 %d", phase_num, state.current_phase)
            else:
                logger.warning(
                    "阶段 %d 暂停: %s (需要人工处理: %s)",
                    phase_num,
                    outcome.message,
                    outcome.requires_human,
                )

        except Exception as e:
            logger.error("阶段 %d 执行失败: %s", phase_num, e, exc_info=True)
            state.get_current_phase().status = BLOCKED

        finally:
            self.store.save(state)

        return state

    def run_all(self, state: PipelineState) -> PipelineState:
        """顺序执行所有尚未完成的阶段。"""
        while state.current_phase <= 7:
            phase_state = state.get_current_phase()

            if phase_state.status == COMPLETED:
                state.current_phase += 1
                continue

            if phase_state.status == BLOCKED:
                logger.warning("阶段 %d 处于阻塞状态，停止推进", state.current_phase)
                break

            state = self.advance(state)

            # 如果阶段需要人工处理，停止推进
            if state.get_current_phase().status == BLOCKED:
                break

            # 如果已是最后一个阶段
            if state.current_phase > 7:
                logger.info("🎉 所有阶段已完成！")
                break

        return state
