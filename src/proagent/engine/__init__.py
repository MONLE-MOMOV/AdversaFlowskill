"""引擎模块 —— 对抗辩论引擎和判定器。"""

from proagent.engine.debate import AdversarialDebateEngine, DebateRound
from proagent.engine.judge import ConvergenceResult, judge_convergence

__all__ = [
    "AdversarialDebateEngine",
    "DebateRound",
    "ConvergenceResult",
    "judge_convergence",
]
