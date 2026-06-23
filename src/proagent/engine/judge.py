"""对抗辩论判定器 —— 规则化收敛和僵局检测。

纯规则引擎，不调用 LLM，确保判定快速、确定、无幻觉风险。
"""

from __future__ import annotations

from typing import Any


class ConvergenceResult:
    """判定结果。"""

    def __init__(
        self,
        is_converged: bool = False,
        is_deadlocked: bool = False,
        resolved_count: int = 0,
        unresolved_items: list[dict[str, Any]] | None = None,
        reason: str = "",
    ):
        self.is_converged = is_converged
        self.is_deadlocked = is_deadlocked
        self.resolved_count = resolved_count
        self.unresolved_items = unresolved_items or []
        self.reason = reason


def judge_convergence(
    challenges: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    round_num: int,
    max_rounds: int,
    previous_unresolved: list[dict[str, Any]] | None = None,
) -> ConvergenceResult:
    """判定本轮对抗是否收敛。

    判定逻辑：
    1. 按提案方回应分类：accept（已解决）、reject（拒绝）、defer（待定）
    2. accept 的项视为解决
    3. reject/defer 的项检查是否与上一轮相同（僵局检测）
    4. 达到最大轮数后仍有未解决的 → 升级人工裁决
    5. 所有项都 accept → 完全收敛

    Args:
        challenges: 挑战方提出的问题列表
        responses: 提案方的回应列表
        round_num: 当前轮数
        max_rounds: 最大轮数
        previous_unresolved: 上一轮的未解决问题列表

    Returns:
        ConvergenceResult 判定结果
    """
    prev_items = previous_unresolved or []
    unresolved: list[dict[str, Any]] = []
    resolved_count = 0

    for i, challenge in enumerate(challenges):
        response = _find_response(i, responses)

        if response is None:
            unresolved.append({
                "challenge": challenge,
                "response": {},
                "reason": "提案方未回应此挑战",
            })
            continue

        action = response.get("action", "defer")

        if action == "accept":
            resolved_count += 1
        elif action == "reject":
            is_repeat = _is_repeat_challenge(challenge, prev_items)
            if is_repeat and round_num >= max_rounds:
                unresolved.append({
                    "challenge": challenge,
                    "response": response,
                    "reason": f"提案方拒绝且已达最大轮数（{round_num}/{max_rounds}），升级人工裁决",
                })
            elif is_repeat:
                unresolved.append({
                    "challenge": challenge,
                    "response": response,
                    "reason": f"连续拒绝（轮数 {round_num}），僵局",
                })
            else:
                unresolved.append({
                    "challenge": challenge,
                    "response": response,
                    "reason": "提案方拒绝，进入下一轮辩论",
                })
        else:  # defer
            if round_num >= max_rounds:
                unresolved.append({
                    "challenge": challenge,
                    "response": response,
                    "reason": f"提案方 defer 且已达最大轮数，升级人工裁决",
                })
            else:
                unresolved.append({
                    "challenge": challenge,
                    "response": response,
                    "reason": "提案方 defer，进入下一轮辩论",
                })

    # 判定
    if len(unresolved) == 0:
        return ConvergenceResult(
            is_converged=True,
            resolved_count=resolved_count,
            reason=f"所有 {resolved_count} 项挑战已解决",
        )

    if round_num >= max_rounds and unresolved:
        return ConvergenceResult(
            is_converged=False,
            is_deadlocked=True,
            resolved_count=resolved_count,
            unresolved_items=unresolved,
            reason=f"已用尽 {max_rounds} 轮，{len(unresolved)} 项未解决，升级人工裁决",
        )

    # 检查是否所有未解决项都处于僵局
    deadlocked_items = [
        u for u in unresolved
        if "僵局" in u.get("reason", "") or "连续拒绝" in u.get("reason", "")
    ]
    if deadlocked_items and len(deadlocked_items) == len(unresolved):
        return ConvergenceResult(
            is_converged=False,
            is_deadlocked=True,
            resolved_count=resolved_count,
            unresolved_items=unresolved,
            reason=f"所有 {len(unresolved)} 项处于僵局状态",
        )

    return ConvergenceResult(
        is_converged=False,
        resolved_count=resolved_count,
        unresolved_items=unresolved,
        reason=f"{resolved_count} 项解决，{len(unresolved)} 项继续辩论",
    )


def _find_response(
    challenge_index: int,
    responses: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """在回应列表中查找对应挑战的回应。"""
    for r in responses:
        if r.get("challenge_index") == challenge_index:
            return r
    if challenge_index < len(responses):
        return responses[challenge_index]
    return None


def _is_repeat_challenge(
    challenge: dict[str, Any],
    previous_unresolved: list[dict[str, Any]],
) -> bool:
    """检查挑战是否与之前的未解决项重复（僵局检测）。"""
    item = challenge.get("item", "")
    if not item:
        return False
    for prev in previous_unresolved:
        prev_item = prev.get("challenge", {}).get("item", "")
        if item == prev_item:
            return True
    return False
