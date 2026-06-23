"""对抗辩论引擎 —— 核心可复用模式。

驱动 Proposer ↔ Challenger 的多轮结构化对抗辩论，
由 Judge 判定收敛/僵局，必要时升级人工裁决。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from proagent.config.roles import Role
from proagent.engine.judge import ConvergenceResult, judge_convergence
from proagent.llm.client import LLMClient
from proagent.llm.prompts import (
    build_challenger_prompt,
    build_proposer_prompt,
    build_rebuttal_prompt,
)

logger = logging.getLogger(__name__)


class DebateRound:
    """单轮辩论的结果。"""

    def __init__(self, round_num: int):
        self.round_num = round_num
        self.proposer_raw: str = ""
        self.challenger_raw: str = ""
        self.proposer_artifact: dict[str, Any] = {}
        self.challenges: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any]] = []
        self.revised_artifact: dict[str, Any] = {}
        self.convergence: ConvergenceResult | None = None


class AdversarialDebateEngine:
    """对抗辩论引擎。

    核心流程：
    1. Proposer 生成初始产物
    2. Challenger 逐条审查
    3. Proposer 回应挑战并修订
    4. Judge 判定收敛
    5. 重复直到收敛或达到最大轮数
    """

    def __init__(
        self,
        llm_client: LLMClient,
        proposer_role: Role,
        challenger_role: Role,
        max_rounds: int = 3,
    ):
        self.llm = llm_client
        self.proposer_role = proposer_role
        self.challenger_role = challenger_role
        self.max_rounds = max_rounds

    def run(
        self,
        task_instruction: str,
        context: dict[str, Any],
        review_criteria: list[str],
        initial_artifact: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """运行完整的对抗辩论流程。

        Args:
            task_instruction: 给 Proposer 的任务指令
            context: 当前上下文（已有产物、需求基线等）
            review_criteria: Challenger 的审查标准
            initial_artifact: 可选的已有产物（如果之前已有）

        Returns:
            包含辩论完整结果的字典：
            - status: converged | deadlocked | escalated
            - final_artifact: 最终产物
            - rounds: 每轮详情
            - unresolved_items: 未解决的争议项
        """
        rounds: list[DebateRound] = []
        current_artifact = initial_artifact or {}
        all_unresolved: list[dict[str, Any]] = []

        for round_num in range(1, self.max_rounds + 1):
            logger.info("=== 辩论第 %d/%d 轮 ===", round_num, self.max_rounds)
            debate = DebateRound(round_num)

            # ---- 步骤 1: Proposer 生成/修订产物 ----
            if round_num == 1 and not current_artifact:
                logger.info("Proposer 生成初始产物...")
                system, messages = build_proposer_prompt(
                    role_system=self.proposer_role.system_prompt,
                    task_instruction=task_instruction,
                    context=context,
                )
                raw = self.llm.send_message(system, messages)
                debate.proposer_raw = raw
                debate.proposer_artifact = self._extract_json(raw)
                current_artifact = debate.proposer_artifact

            elif round_num > 1 and all_unresolved:
                # 回应上一轮的挑战
                logger.info("Proposer 回应 %d 项挑战...", len(all_unresolved))
                system, messages = build_rebuttal_prompt(
                    role_system=self.proposer_role.system_prompt,
                    original_artifact=current_artifact,
                    challenges=all_unresolved,
                    task_instruction=task_instruction,
                )
                raw = self.llm.send_message(system, messages)
                debate.proposer_raw = raw
                result = self._extract_json(raw)

                debate.responses = result.get("responses", [])
                revised = result.get("revised_artifact", {})
                if revised:
                    debate.revised_artifact = revised
                    current_artifact = revised

            # ---- 步骤 2: Challenger 审查 ----
            logger.info("Challenger 审查产物...")
            system, messages = build_challenger_prompt(
                role_system=self.challenger_role.system_prompt,
                artifact=current_artifact,
                review_criteria=review_criteria,
                context=context,
            )
            raw = self.llm.send_message(system, messages)
            debate.challenger_raw = raw
            debate.challenges = self._extract_json(raw)

            # 确保 challenges 是列表
            if isinstance(debate.challenges, dict):
                debate.challenges = [debate.challenges]

            if not debate.challenges:
                # 挑战方未发现问题
                logger.info("挑战方未发现问题，收敛！")
                debate.convergence = ConvergenceResult(
                    is_converged=True,
                    resolved_count=0,
                    reason="挑战方未发现任何问题",
                )
                rounds.append(debate)
                return self._build_result("converged", current_artifact, rounds, [])

            # ---- 步骤 3: Proposer 逐条回应（同轮内第二次调用） ----
            if round_num == 1 or not debate.responses:
                logger.info("Proposer 逐条回应 %d 项挑战...", len(debate.challenges))
                system, messages = build_rebuttal_prompt(
                    role_system=self.proposer_role.system_prompt,
                    original_artifact=current_artifact,
                    challenges=debate.challenges,
                    task_instruction=task_instruction,
                )
                raw = self.llm.send_message(system, messages)
                debate.proposer_raw = raw
                result = self._extract_json(raw)
                debate.responses = result.get("responses", [])
                revised = result.get("revised_artifact", {})
                if revised:
                    debate.revised_artifact = revised
                    current_artifact = revised

            # ---- 步骤 4: Judge 判定 ----
            result = judge_convergence(
                challenges=debate.challenges,
                responses=debate.responses,
                round_num=round_num,
                max_rounds=self.max_rounds,
                previous_unresolved=all_unresolved,
            )
            debate.convergence = result
            rounds.append(debate)

            if result.is_converged:
                logger.info("✅ 辩论收敛: %s", result.reason)
                return self._build_result("converged", current_artifact, rounds, [])

            # 更新未解决项列表
            all_unresolved = result.unresolved_items

            if result.is_deadlocked:
                logger.warning("🚫 辩论僵局，升级人工裁决: %s", result.reason)
                return self._build_result(
                    "deadlocked", current_artifact, rounds, all_unresolved
                )

            logger.info("继续下一轮辩论...")

        # 用尽所有轮数
        logger.warning("已用尽 %d 轮辩论", self.max_rounds)
        return self._build_result(
            "escalated", current_artifact, rounds, all_unresolved
        )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

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
        elif "```" in text:
            try:
                start = text.index("```") + 3
                end = text.index("```", start)
                return json.loads(text[start:end].strip())
            except (ValueError, json.JSONDecodeError):
                pass

        # 尝试直接解析
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            logger.warning("无法从响应中解析 JSON")
            return {"raw_text": text}

    @staticmethod
    def _build_result(
        status: str,
        final_artifact: dict[str, Any],
        rounds: list[DebateRound],
        unresolved: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """构建最终结果字典。"""
        return {
            "status": status,
            "final_artifact": final_artifact,
            "total_rounds": len(rounds),
            "rounds": [
                {
                    "round_num": r.round_num,
                    "challenges": r.challenges,
                    "responses": r.responses,
                    "converged": r.convergence.is_converged if r.convergence else False,
                }
                for r in rounds
            ],
            "unresolved_items": unresolved,
        }
